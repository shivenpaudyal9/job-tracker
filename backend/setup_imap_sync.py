"""
IMAP Email Sync Setup (For Personal Outlook Accounts)

This is MUCH simpler than Microsoft Graph for personal accounts.
No Azure Portal needed!

Setup Steps:
1. Enable IMAP in your Outlook settings
2. Generate an app-specific password
3. Configure this script
4. Run automated sync
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.processor import EmailProcessor
import os
from dotenv import load_dotenv

load_dotenv()


class IMAPEmailSync:
    """Sync emails from Outlook via IMAP"""

    def __init__(self, email_address: str, password: str):
        self.email_address = email_address
        self.password = password
        self.imap_server = "outlook.office365.com"
        self.imap_port = 993

    def connect(self):
        """Connect to IMAP server"""
        print(f"Connecting to {self.imap_server}...")
        self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        self.mail.login(self.email_address, self.password)
        print("[OK] Connected successfully!")
        return self.mail

    def get_emails_since(self, days_back=30):
        """Fetch emails from the last N days"""
        self.mail.select("inbox")

        # Calculate date
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

        # Search for emails
        print(f"Searching for emails since {since_date}...")
        status, messages = self.mail.search(None, f'(SINCE "{since_date}")')

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} emails")

        return email_ids

    def fetch_email(self, email_id):
        """Fetch a single email"""
        status, msg_data = self.mail.fetch(email_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                # Decode subject
                subject = self.decode_header_value(msg["Subject"])

                # Get sender
                from_addr = msg.get("From", "")

                # Get date
                date_str = msg.get("Date", "")
                email_date = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.now()

                # Get body
                body_text = ""
                body_html = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            body_text = part.get_payload(decode=True).decode(errors='ignore')
                        elif content_type == "text/html":
                            body_html = part.get_payload(decode=True).decode(errors='ignore')
                else:
                    body_text = msg.get_payload(decode=True).decode(errors='ignore')

                return {
                    "subject": subject,
                    "from": from_addr,
                    "date": email_date,
                    "body_text": body_text,
                    "body_html": body_html,
                    "message_id": msg.get("Message-ID", f"imap_{email_id.decode()}")
                }

        return None

    def decode_header_value(self, value):
        """Decode email header value"""
        if not value:
            return ""

        decoded_parts = decode_header(value)
        result = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                result += part

        return result

    def sync_to_database(self, days_back=30, limit=None):
        """Sync emails to database"""
        db = SessionLocal()
        processor = EmailProcessor(db)

        try:
            self.connect()
            email_ids = self.get_emails_since(days_back)

            if limit:
                email_ids = email_ids[:limit]

            processed = 0
            errors = 0

            for i, email_id in enumerate(email_ids, 1):
                try:
                    print(f"\n[{i}/{len(email_ids)}] Processing email {email_id.decode()}...")

                    email_data = self.fetch_email(email_id)
                    if not email_data:
                        continue

                    # Process through the system
                    result = processor.process_email(
                        outlook_message_id=email_data["message_id"],
                        conversation_id=email_data["message_id"],
                        received_datetime=email_data["date"],
                        outlook_from=email_data["from"],
                        outlook_to=self.email_address,
                        outlook_subject=email_data["subject"],
                        body_text=email_data["body_text"],
                        body_html=email_data["body_html"],
                        raw_headers={}
                    )

                    print(f"  Company: {result.get('company_name', 'N/A')}")
                    print(f"  Job: {result.get('job_title', 'N/A')}")
                    print(f"  Status: {result.get('status', 'N/A')}")

                    processed += 1

                except Exception as e:
                    print(f"  [ERROR] {e}")
                    errors += 1

            print(f"\n{'='*80}")
            print(f"SYNC COMPLETE")
            print(f"{'='*80}")
            print(f"Processed: {processed}/{len(email_ids)}")
            print(f"Errors: {errors}")

        finally:
            db.close()
            self.mail.logout()


def main():
    print("="*80)
    print("IMAP EMAIL SYNC SETUP")
    print("="*80)

    # Get credentials from environment or prompt
    email_address = os.getenv("OUTLOOK_EMAIL")
    password = os.getenv("OUTLOOK_APP_PASSWORD")

    if not email_address or not password:
        print("\nCredentials not found in .env file")
        print("\nPlease add to your .env file:")
        print("  OUTLOOK_EMAIL=your.email@outlook.com")
        print("  OUTLOOK_APP_PASSWORD=your_app_specific_password")
        print("\nSee SETUP_IMAP.md for instructions on getting an app password")
        return

    print(f"\nEmail: {email_address}")
    print(f"Password: {'*' * 16}")

    syncer = IMAPEmailSync(email_address, password)

    try:
        print("\nTesting connection...")
        syncer.connect()
        print("[OK] Connection successful!")

        print("\nStarting sync...")
        syncer.sync_to_database(days_back=30, limit=10)  # Start with 10 emails for testing

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nTroubleshooting:")
        print("1. Check your email and password are correct")
        print("2. Make sure IMAP is enabled in Outlook settings")
        print("3. Use an app-specific password (not your regular password)")
        print("\nSee SETUP_IMAP.md for detailed instructions")


if __name__ == "__main__":
    main()
