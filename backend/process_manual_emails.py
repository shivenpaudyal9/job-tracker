"""
Manual Email Processor

Process job application emails without Microsoft Graph.
Just paste your email content and let the system extract the data.

Usage:
    python process_manual_emails.py
"""

from app.database import SessionLocal
from app.processor import EmailProcessor
from app.models import ApplicationStatus
from datetime import datetime

print("=" * 80)
print("MANUAL EMAIL PROCESSOR")
print("=" * 80)
print("\nThis will process your job application emails and extract:")
print("  - Company name")
print("  - Job title")
print("  - Application status")
print("  - Action items")
print("  - Links\n")

# Sample emails from your real examples
SAMPLE_EMAILS = [
    {
        "subject": "Your application was sent to Eleven Recruiting",
        "body": """Your application was sent to Eleven Recruiting
Eleven Recruiting
Workday Reporting Analyst
Eleven Recruiting · Los Angeles, CA (On-site)
Applied on January 3, 2026""",
        "from_address": "noreply@linkedin.com",
        "date": datetime(2026, 1, 3)
    },
    {
        "subject": "Thank you for your application - Data Analyst",
        "body": """Dear Shiven

Thank you very much for your interest in employment opportunities with Genworth and,
specifically, for your application for the Data Analyst position.

Should your application be selected among the most qualified, a Genworth recruiter
will contact you regarding next steps.

Thank you again for your interest in Genworth.

Sincerely,
Genworth Recruitment Services""",
        "from_address": "gnw@myworkday.com",
        "date": datetime(2026, 1, 4)
    },
    {
        "subject": "Application Received - Data Analyst",
        "body": """Hi Shiven,

Thank you for your interest in The Voleon Group!

We wanted to let you know we received your application for Data Analyst, and we are
delighted that you would consider joining our team.

Our team will review your application and will be in touch if your qualifications
match our needs for the role.

Thanks again,
The Voleon Group""",
        "from_address": "careers@voleon.com",
        "date": datetime(2026, 1, 5)
    },
]

def process_email_manual(subject, body, from_address, date):
    """Process a single email through the system"""
    db = SessionLocal()
    processor = EmailProcessor(db)

    try:
        # Generate a fake Outlook message ID for manual emails
        import hashlib
        message_id = f"manual_{hashlib.md5(f'{subject}{from_address}{date}'.encode()).hexdigest()}"

        # Process the email
        result = processor.process_email(
            outlook_message_id=message_id,
            conversation_id=message_id,
            received_datetime=date,
            outlook_from=from_address,
            outlook_to="your_email@example.com",
            outlook_subject=subject,
            body_html=body,
            body_text=body,
            raw_headers={}
        )

        print(f"\n{'='*80}")
        print(f"PROCESSED: {subject[:50]}...")
        print(f"{'='*80}")
        print(f"[OK] Company: {result.get('company_name', 'N/A')}")
        print(f"[OK] Job Title: {result.get('job_title', 'N/A')}")
        print(f"[OK] Status: {result.get('status', 'N/A')}")
        print(f"[OK] Confidence: {result.get('confidence', 0):.2f}")

        if result.get('application_id'):
            print(f"[OK] Application ID: {result['application_id']}")
        if result.get('needs_review'):
            print(f"[WARNING] Flagged for manual review")

        return result

    except Exception as e:
        print(f"\n[ERROR] Error processing email: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def main():
    print("\nProcessing sample emails...\n")

    results = []
    for i, email in enumerate(SAMPLE_EMAILS, 1):
        print(f"\n[{i}/{len(SAMPLE_EMAILS)}] Processing...")
        result = process_email_manual(
            subject=email['subject'],
            body=email['body'],
            from_address=email['from_address'],
            date=email['date']
        )
        if result:
            results.append(result)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Emails processed: {len(results)}/{len(SAMPLE_EMAILS)}")
    print(f"Applications created/updated: {len([r for r in results if r.get('application_id')])}")
    print(f"Needs review: {len([r for r in results if r.get('needs_review')])}")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. View applications:")
    print("   curl http://127.0.0.1:8000/applications")

    print("\n2. Export to Excel:")
    print("   curl -X POST http://127.0.0.1:8000/export")

    print("\n3. Add your own emails:")
    print("   Edit this file and add more emails to SAMPLE_EMAILS list")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
