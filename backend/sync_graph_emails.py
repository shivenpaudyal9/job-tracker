"""
Sync Outlook Emails via Microsoft Graph API with Token Caching

This script:
1. Authenticates once using device code flow
2. Caches the token for future use
3. Fetches job application emails
4. Processes them through the extraction pipeline
5. Stores in database
"""

import os
import sys
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from msal import PublicClientApplication, SerializableTokenCache
import requests
from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.processor import EmailProcessor
from app.models import Application

load_dotenv()

# Configuration
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "consumers")
USER_EMAIL = os.getenv("MICROSOFT_USER_EMAIL")

SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/User.Read"
]

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
TOKEN_CACHE_FILE = Path(__file__).parent / ".token_cache.bin"


class GraphEmailSync:
    """Microsoft Graph Email Sync with Token Caching"""

    def __init__(self):
        self.cache = SerializableTokenCache()

        # Load cached token if exists
        if TOKEN_CACHE_FILE.exists():
            with open(TOKEN_CACHE_FILE, "r") as f:
                self.cache.deserialize(f.read())

        # Create MSAL app with cache
        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY,
            token_cache=self.cache
        )

        self.access_token = None

    def _save_cache(self):
        """Save token cache to disk"""
        if self.cache.has_state_changed:
            with open(TOKEN_CACHE_FILE, "w") as f:
                f.write(self.cache.serialize())

    def authenticate(self):
        """Get access token (from cache or new authentication)"""

        # Try to get token from cache first
        accounts = self.app.get_accounts()
        if accounts:
            print(f"Found cached account: {accounts[0].get('username')}")
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                print("[OK] Using cached token")
                self.access_token = result["access_token"]
                return True

        # No cached token - need device code flow
        print("\n" + "="*80)
        print("AUTHENTICATION REQUIRED")
        print("="*80)

        flow = self.app.initiate_device_flow(scopes=SCOPES)

        if "user_code" not in flow:
            print(f"[ERROR] Failed to initiate device code flow: {flow}")
            return False

        print(f"\n1. Open: {flow['verification_uri']}")
        print(f"\n2. Enter code: {flow['user_code']}")
        print(f"\n3. Sign in with: {USER_EMAIL}")
        print(f"\nWaiting for authentication (expires in {flow.get('expires_in', 900) // 60} min)...")
        print("="*80)

        result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            print("\n[SUCCESS] Authentication complete!")
            self.access_token = result["access_token"]
            self._save_cache()
            return True
        else:
            print(f"\n[ERROR] Authentication failed: {result.get('error_description')}")
            return False

    def get_user_info(self):
        """Get authenticated user's profile"""
        if not self.access_token:
            return None

        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers
        )

        if response.status_code == 200:
            return response.json()
        return None

    def fetch_emails(self, days_back=30, max_emails=200):
        """
        Fetch emails from the last N days

        Args:
            days_back: How many days back to fetch (default 30)
            max_emails: Maximum number of emails to fetch (default 200)

        Returns:
            List of email dictionaries
        """
        if not self.access_token:
            print("[ERROR] Not authenticated")
            return []

        # Calculate date filter
        start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        date_filter = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        headers = {"Authorization": f"Bearer {self.access_token}"}

        # Build query - fetch all emails
        query = (
            f"https://graph.microsoft.com/v1.0/me/messages?"
            f"$filter=receivedDateTime ge {date_filter}&"
            f"$top=50&"
            f"$select=id,conversationId,subject,from,receivedDateTime,bodyPreview,body,toRecipients,internetMessageHeaders&"
            f"$orderby=receivedDateTime desc"
        )

        print(f"\nFetching emails from last {days_back} days...")

        all_emails = []

        while query and len(all_emails) < max_emails:
            response = requests.get(query, headers=headers)

            if response.status_code != 200:
                print(f"[ERROR] Failed to fetch emails: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                break

            data = response.json()
            emails = data.get("value", [])
            all_emails.extend(emails)

            print(f"  Fetched {len(all_emails)} emails so far...")

            # Check for next page
            query = data.get("@odata.nextLink")

        print(f"[OK] Fetched {len(all_emails)} total emails")
        return all_emails[:max_emails]


def main():
    print("="*80)
    print("MICROSOFT GRAPH EMAIL SYNC")
    print("="*80)

    # Initialize sync
    sync = GraphEmailSync()

    # Authenticate
    if not sync.authenticate():
        print("\n[ERROR] Authentication failed. Exiting.")
        sys.exit(1)

    # Get user info
    user = sync.get_user_info()
    if user:
        print(f"\n[OK] Authenticated as: {user.get('displayName')} ({user.get('mail') or user.get('userPrincipalName')})")

    # Fetch emails
    print("\n" + "="*80)
    print("FETCHING EMAILS")
    print("="*80)

    all_emails = sync.fetch_emails(days_back=30, max_emails=200)

    if not all_emails:
        print("\n[WARN] No emails found")
        return

    # Process emails
    print("\n" + "="*80)
    print(f"PROCESSING {len(all_emails)} EMAILS")
    print("="*80)

    db = SessionLocal()
    processor = EmailProcessor(db)

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for i, email in enumerate(all_emails, 1):
        # Extract email data
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

        headers = email.get('internetMessageHeaders', [])
        headers_dict = {h.get('name'): h.get('value') for h in headers} if headers else {}

        received_dt = datetime.fromisoformat(received.replace('Z', '+00:00'))

        # Show progress
        if i % 10 == 0 or i == 1:
            print(f"\n[{i}/{len(all_emails)}] {subject[:60]}...")

        try:
            # Process through the extraction pipeline
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
                processed_count += 1
                if processed_count <= 5 and result.application_id:  # Show first 5
                    # Get the application to show details
                    app_obj = db.query(Application).filter(Application.id == result.application_id).first()
                    if app_obj:
                        print(f"  [OK] {app_obj.company_name} - {app_obj.job_title} (confidence: {result.confidence:.0%})")
            else:
                skipped_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 3:  # Show first 3 errors
                print(f"  [ERROR] {str(e)[:100]}")

    db.close()

    # Summary
    print("\n" + "="*80)
    print("SYNC COMPLETE")
    print("="*80)
    print(f"Total emails fetched: {len(all_emails)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (duplicates/not job-related): {skipped_count}")
    print(f"Errors: {error_count}")

    if processed_count > 0:
        print("\n✓ Job applications have been added to the database!")
        print("  View them at: http://localhost:8000/applications")
        print("\n  Next steps:")
        print("  1. Start the API: uvicorn app.main:app --reload")
        print("  2. Export to Excel: python export_to_excel.py")


if __name__ == "__main__":
    main()
