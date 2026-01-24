"""
Sync API Router - Multi-user version
Handles per-user Outlook connection and email synchronization
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timezone
from pathlib import Path
import os
import logging

from app.database import get_db
from app.models import SyncState, Application, User
from app.auth import get_current_user
from msal import PublicClientApplication, SerializableTokenCache
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

router = APIRouter(prefix="/sync", tags=["sync"])

# Initialize Groq client for LLM extraction
def get_llm_client():
    """Get Groq client if API key is configured"""
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        return Groq(api_key=api_key)
    return None


logger = logging.getLogger(__name__)

# Configuration
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "consumers")
SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/User.Read"
]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Per-user state for device code flow (keyed by user_id)
_device_flow_states: Dict[int, dict] = {}
# Per-user sync locks (keyed by user_id)
_sync_locks: Dict[int, bool] = {}


# Pydantic models
class ConnectStartResponse(BaseModel):
    verification_uri: str
    user_code: str
    expires_in: int
    interval: int = 5
    message: str


class ConnectPollResponse(BaseModel):
    connected: bool
    message: str
    error: Optional[str] = None


class SyncRunResponse(BaseModel):
    success: bool
    message: str
    emails_fetched: int = 0
    emails_processed: int = 0
    applications_created: int = 0
    applications_updated: int = 0
    errors_count: int = 0


class SyncStatusResponse(BaseModel):
    is_connected: bool
    is_running: bool
    last_sync_at: Optional[datetime] = None
    last_sync_counts: Optional[dict] = None


def get_msal_app_for_user(user: User):
    """Get MSAL application with user's token cache"""
    cache = SerializableTokenCache()

    # Load user's token cache from database
    if user.outlook_token_cache:
        cache.deserialize(user.outlook_token_cache)

    app = PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )

    return app, cache


def save_user_token_cache(user: User, cache: SerializableTokenCache, db: Session):
    """Save token cache to user's database record"""
    if cache.has_state_changed:
        user.outlook_token_cache = cache.serialize()
        user.is_outlook_connected = True
        db.commit()


def is_user_authenticated(user: User, db: Session) -> bool:
    """Check if user is authenticated with Outlook"""
    if not user.outlook_token_cache:
        return False

    app, cache = get_msal_app_for_user(user)
    accounts = app.get_accounts()

    if not accounts:
        return False

    # Try silent token acquisition
    result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if result and "access_token" in result:
        # Save refreshed cache
        save_user_token_cache(user, cache, db)
        return True

    return False


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Job Tracker Sync API",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/status", response_model=SyncStatusResponse)
def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current sync status for user"""

    # Check if connected
    is_connected = is_user_authenticated(current_user, db)

    # Get last sync for this user
    last_sync = db.query(SyncState).filter(
        SyncState.user_id == current_user.id
    ).order_by(desc(SyncState.started_at)).first()

    # Check user's sync lock
    is_running = _sync_locks.get(current_user.id, False)

    response = SyncStatusResponse(
        is_connected=is_connected,
        is_running=is_running,
        last_sync_at=last_sync.completed_at if last_sync else None,
        last_sync_counts={
            "emails_fetched": last_sync.emails_fetched,
            "emails_processed": last_sync.emails_processed,
            "applications_created": last_sync.applications_created,
            "errors_count": last_sync.errors_count
        } if last_sync else None
    )

    return response


@router.post("/connect/start", response_model=ConnectStartResponse)
def start_device_code_flow(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start Microsoft device code authentication flow for user"""

    app, cache = get_msal_app_for_user(current_user)

    # Initiate device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)

    if "user_code" not in flow:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate device code flow: {flow.get('error_description', 'Unknown error')}"
        )

    # Store flow state for this user
    _device_flow_states[current_user.id] = {
        "flow": flow,
        "app": app,
        "cache": cache,
        "started_at": datetime.now(timezone.utc)
    }

    return ConnectStartResponse(
        verification_uri=flow["verification_uri"],
        user_code=flow["user_code"],
        expires_in=flow.get("expires_in", 900),
        interval=flow.get("interval", 5),
        message=f"Go to {flow['verification_uri']} and enter code: {flow['user_code']}"
    )


@router.post("/connect/poll", response_model=ConnectPollResponse)
def poll_device_code_auth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Poll for device code authentication completion"""

    user_state = _device_flow_states.get(current_user.id)

    if not user_state or "flow" not in user_state:
        raise HTTPException(
            status_code=400,
            detail="No authentication flow in progress. Call /sync/connect/start first."
        )

    app = user_state["app"]
    flow = user_state["flow"]
    cache = user_state["cache"]

    # Try to acquire token (non-blocking)
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        # Success! Save cache to user's database record
        save_user_token_cache(current_user, cache, db)

        # Clear flow state for this user
        _device_flow_states.pop(current_user.id, None)

        logger.info(f"Device code authentication successful for user {current_user.id}")

        return ConnectPollResponse(
            connected=True,
            message="Successfully connected to Outlook!"
        )

    elif "error" in result:
        error = result.get("error")

        # Check if still pending
        if error == "authorization_pending":
            return ConnectPollResponse(
                connected=False,
                message="Waiting for user to complete authentication...",
                error=None
            )

        # Other errors
        _device_flow_states.pop(current_user.id, None)

        return ConnectPollResponse(
            connected=False,
            message="Authentication failed",
            error=result.get("error_description", error)
        )

    return ConnectPollResponse(
        connected=False,
        message="Polling...",
        error=None
    )


@router.post("/disconnect")
def disconnect_outlook(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Outlook for user"""
    current_user.outlook_token_cache = None
    current_user.is_outlook_connected = False
    current_user.outlook_email = None
    db.commit()

    # Clear any pending flow state
    _device_flow_states.pop(current_user.id, None)

    return {"message": "Outlook disconnected successfully"}


@router.post("/run", response_model=SyncRunResponse)
async def run_sync(
    background_tasks: BackgroundTasks,
    days_back: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger email sync for user (runs in background)"""

    user_id = current_user.id

    # Check if already running for this user
    if _sync_locks.get(user_id, False):
        raise HTTPException(status_code=409, detail="Sync already in progress")

    # Check if authenticated
    if not is_user_authenticated(current_user, db):
        raise HTTPException(
            status_code=401,
            detail="Not connected to Outlook. Please connect first via /sync/connect/start"
        )

    # Create sync state record
    sync_state = SyncState(
        user_id=user_id,
        started_at=datetime.now(timezone.utc),
        is_running=True,
        is_connected=True
    )
    db.add(sync_state)
    db.commit()
    db.refresh(sync_state)

    sync_state_id = sync_state.id

    # Run sync in background
    async def run_sync_task():
        _sync_locks[user_id] = True

        try:
            # Import here to avoid circular dependency
            from app.database import SessionLocal
            from app.processor import EmailProcessor
            from datetime import timedelta
            import requests

            db_session = SessionLocal()

            # Reload user and sync_state in new session
            user = db_session.query(User).filter(User.id == user_id).first()
            sync_record = db_session.query(SyncState).filter(SyncState.id == sync_state_id).first()

            # Get token
            app, cache = get_msal_app_for_user(user)
            accounts = app.get_accounts()

            if not accounts:
                sync_record.error_message = "No accounts found"
                sync_record.success = False
                sync_record.is_running = False
                sync_record.completed_at = datetime.now(timezone.utc)
                db_session.commit()
                db_session.close()
                _sync_locks[user_id] = False
                return

            result = app.acquire_token_silent(SCOPES, account=accounts[0])

            if not result or "access_token" not in result:
                sync_record.error_message = "Failed to acquire token"
                sync_record.success = False
                sync_record.is_running = False
                sync_record.completed_at = datetime.now(timezone.utc)
                db_session.commit()
                db_session.close()
                _sync_locks[user_id] = False
                return

            access_token = result["access_token"]

            # Fetch emails
            start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            date_filter = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

            headers = {"Authorization": f"Bearer {access_token}"}
            query = (
                f"https://graph.microsoft.com/v1.0/me/messages?"
                f"$filter=receivedDateTime ge {date_filter}&"
                f"$top=50&"
                f"$select=id,conversationId,subject,from,receivedDateTime,bodyPreview,body,toRecipients,internetMessageHeaders&"
                f"$orderby=receivedDateTime desc"
            )

            all_emails = []
            while query and len(all_emails) < 200:
                response = requests.get(query, headers=headers)
                if response.status_code != 200:
                    break

                data = response.json()
                emails = data.get("value", [])
                all_emails.extend(emails)
                query = data.get("@odata.nextLink")

            sync_record.emails_fetched = len(all_emails)

            # Process emails with user_id and LLM client (Groq)
            llm_client = get_llm_client()
            processor = EmailProcessor(db_session, llm_client=llm_client, user_id=user_id)
            processed = 0
            created = 0
            errors = 0

            for email in all_emails:
                try:
                    message_id = email.get('id', '')
                    conversation_id = email.get('conversationId', '')
                    subject = email.get('subject', '')
                    received = email.get('receivedDateTime', '')

                    from_addr = email.get('from', {}).get('emailAddress', {})
                    from_email = from_addr.get('address', '')

                    to_addrs = email.get('toRecipients', [])
                    to_email = to_addrs[0].get('emailAddress', {}).get('address', '') if to_addrs else ''

                    body = email.get('body', {})
                    body_html = body.get('content', '')
                    body_text = email.get('bodyPreview', '')

                    headers_list = email.get('internetMessageHeaders', [])
                    headers_dict = {h.get('name'): h.get('value') for h in headers_list} if headers_list else {}

                    received_dt = datetime.fromisoformat(received.replace('Z', '+00:00'))

                    result = processor.process_email(
                        outlook_message_id=message_id,
                        conversation_id=conversation_id,
                        received_datetime=received_dt,
                        outlook_from=from_email,
                        outlook_to=to_email,
                        outlook_subject=subject,
                        body_html=body_html,
                        body_text=body_text,
                        raw_headers=headers_dict
                    )

                    if result and result.success:
                        processed += 1
                        if result.is_new_application:
                            created += 1

                except Exception as e:
                    logger.error(f"Error processing email: {e}")
                    errors += 1

            # Update sync state
            sync_record.emails_processed = processed
            sync_record.applications_created = created
            sync_record.errors_count = errors
            sync_record.success = True
            sync_record.is_running = False
            sync_record.completed_at = datetime.now(timezone.utc)

            db_session.commit()
            db_session.close()

        except Exception as e:
            logger.error(f"Sync failed for user {user_id}: {e}")
            try:
                db_session = SessionLocal()
                sync_record = db_session.query(SyncState).filter(SyncState.id == sync_state_id).first()
                if sync_record:
                    sync_record.error_message = str(e)
                    sync_record.success = False
                    sync_record.is_running = False
                    sync_record.completed_at = datetime.now(timezone.utc)
                    db_session.commit()
                db_session.close()
            except:
                pass

        finally:
            _sync_locks[user_id] = False

    # Schedule background task
    background_tasks.add_task(run_sync_task)

    return SyncRunResponse(
        success=True,
        message="Sync started in background",
        emails_fetched=0,
        emails_processed=0,
        applications_created=0,
        errors_count=0
    )


@router.get("/export/excel")
def export_excel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export user's applications to Excel file"""
    from app.excel_exporter import export_to_excel

    output_path = f"job_applications_{current_user.id}.xlsx"
    file_path = export_to_excel(db, output_path, user_id=current_user.id)

    if not Path(file_path).exists():
        raise HTTPException(status_code=500, detail="Failed to generate Excel file")

    return FileResponse(
        path=file_path,
        filename="job_applications.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
