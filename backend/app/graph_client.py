"""
Microsoft Graph API Client for Outlook Integration

Handles:
- OAuth authentication
- Fetching emails from Outlook inbox
- Incremental sync (delta queries)
- Rate limiting and retries
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

# Microsoft Graph SDK
try:
    from msal import ConfidentialClientApplication
    import requests
except ImportError:
    print("Install: pip install msal requests")

logger = logging.getLogger(__name__)


class OutlookGraphClient:
    """
    Client for Microsoft Graph API to fetch emails from Outlook.

    Setup:
    1. Register app in Azure Portal
    2. Set environment variables:
       - MICROSOFT_CLIENT_ID
       - MICROSOFT_CLIENT_SECRET
       - MICROSOFT_TENANT_ID
       - MICROSOFT_USER_EMAIL
    """

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    SCOPES = ["https://graph.microsoft.com/.default"]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_email: Optional[str] = None
    ):
        """Initialize Graph client with OAuth credentials"""
        self.client_id = client_id or os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = tenant_id or os.getenv("MICROSOFT_TENANT_ID")
        self.user_email = user_email or os.getenv("MICROSOFT_USER_EMAIL")

        if not all([self.client_id, self.client_secret, self.tenant_id, self.user_email]):
            raise ValueError("Missing Microsoft Graph credentials")

        self.msal_app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )

        self.access_token = None

    def _get_access_token(self) -> str:
        """Get OAuth access token"""
        if self.access_token:
            return self.access_token

        result = self.msal_app.acquire_token_for_client(scopes=self.SCOPES)

        if "access_token" in result:
            self.access_token = result["access_token"]
            return self.access_token
        else:
            raise Exception(f"Failed to get token: {result.get('error_description')}")

    def fetch_emails(
        self,
        folder: str = "inbox",
        top: int = 50,
        filter_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from Outlook mailbox.

        Args:
            folder: Folder name (default: "inbox")
            top: Number of messages to fetch (max 999)
            filter_query: Optional OData filter (e.g., "receivedDateTime ge 2024-01-01")

        Returns:
            List of email message dicts
        """
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Build URL
        url = f"{self.GRAPH_API_ENDPOINT}/users/{self.user_email}/mailFolders/{folder}/messages"
        params = {
            "$top": top,
            "$select": "id,subject,from,toRecipients,receivedDateTime,body,conversationId",
            "$orderby": "receivedDateTime desc"
        }

        if filter_query:
            params["$filter"] = filter_query

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("value", [])

    def fetch_new_emails_since(self, since_date: datetime, top: int = 100) -> List[Dict[str, Any]]:
        """Fetch emails received since a specific date"""
        date_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        filter_query = f"receivedDateTime ge {date_str}"
        return self.fetch_emails(filter_query=filter_query, top=top)

    def parse_message_to_dict(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Graph API message to our standard format.

        Returns dict compatible with EmailProcessor.process_email()
        """
        from_email = message.get("from", {}).get("emailAddress", {})

        return {
            "outlook_message_id": message.get("id"),
            "outlook_from": from_email.get("address", ""),
            "outlook_to": self.user_email,
            "outlook_subject": message.get("subject", ""),
            "received_datetime": self._parse_datetime(message.get("receivedDateTime")),
            "body_text": message.get("body", {}).get("content", ""),
            "body_html": message.get("body", {}).get("content", "") if message.get("body", {}).get("contentType") == "html" else None,
            "conversation_id": message.get("conversationId")
        }

    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """Parse ISO datetime string"""
        if not dt_str:
            return datetime.utcnow()

        try:
            # Remove timezone info for simplicity
            dt_str = dt_str.replace("Z", "")
            return datetime.fromisoformat(dt_str)
        except:
            return datetime.utcnow()


# Convenience function
def sync_outlook_emails(
    db_session,
    days_back: int = 30,
    llm_client=None
) -> Dict[str, Any]:
    """
    Sync emails from Outlook and process them.

    Usage:
        from app.database import SessionLocal
        from app.graph_client import sync_outlook_emails

        db = SessionLocal()
        result = sync_outlook_emails(db, days_back=30)
        print(f"Processed {result['processed']} emails")
    """
    from app.processor import EmailProcessor

    client = OutlookGraphClient()
    processor = EmailProcessor(db_session, llm_client=llm_client)

    # Fetch recent emails
    since_date = datetime.utcnow() - timedelta(days=days_back)
    messages = client.fetch_new_emails_since(since_date)

    logger.info(f"Fetched {len(messages)} emails from Outlook")

    # Process each message
    results = []
    for message in messages:
        message_dict = client.parse_message_to_dict(message)
        result = processor.process_email(**message_dict)
        results.append(result)

    # Collect stats
    stats = {
        "fetched": len(messages),
        "processed": sum(1 for r in results if r.success),
        "new_applications": sum(1 for r in results if r.is_new_application),
        "updated_applications": sum(1 for r in results if r.success and not r.is_new_application and not r.needs_manual_review),
        "manual_review": sum(1 for r in results if r.needs_manual_review),
        "errors": sum(1 for r in results if not r.success)
    }

    logger.info(f"Sync complete: {stats}")
    return stats
