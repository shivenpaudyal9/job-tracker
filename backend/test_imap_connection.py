"""
Test IMAP Connection - Detailed Diagnostics

This will help diagnose why IMAP isn't connecting.
"""

import imaplib
import os
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("OUTLOOK_EMAIL")
password = os.getenv("OUTLOOK_APP_PASSWORD")

print("="*80)
print("IMAP CONNECTION DIAGNOSTIC")
print("="*80)

print(f"\nEmail: {email}")
print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
print(f"Password length: {len(password) if password else 0} characters")

# Try different IMAP configurations
configs = [
    ("outlook.office365.com", 993, "SSL"),
    ("imap-mail.outlook.com", 993, "SSL"),
    ("outlook.office365.com", 143, "STARTTLS"),
]

for server, port, method in configs:
    print(f"\nTrying {server}:{port} ({method})...")
    try:
        if method == "SSL":
            mail = imaplib.IMAP4_SSL(server, port)
        else:
            mail = imaplib.IMAP4(server, port)
            mail.starttls()

        print(f"  [OK] Connected to server")

        # Try to login
        try:
            result = mail.login(email, password)
            print(f"  [SUCCESS] Login successful!")
            print(f"  Result: {result}")

            # List mailboxes
            status, mailboxes = mail.list()
            print(f"  Mailboxes: {len(mailboxes)} found")

            mail.logout()
            print(f"\n{'='*80}")
            print(f"SUCCESS! Use this configuration:")
            print(f"  Server: {server}")
            print(f"  Port: {port}")
            print(f"  Method: {method}")
            print(f"{'='*80}")
            break

        except Exception as e:
            print(f"  [FAILED] Login failed: {e}")

    except Exception as e:
        print(f"  [FAILED] Connection failed: {e}")

print("\n" + "="*80)
print("TROUBLESHOOTING TIPS")
print("="*80)
print("""
If all attempts failed:

1. VERIFY IMAP IS ENABLED:
   - Go to: https://outlook.live.com/mail/0/options/mail/sync
   - Make sure "Let devices and apps use IMAP" is ON
   - Click Save

2. CHECK APP PASSWORD:
   - Go to: https://account.microsoft.com/security
   - Click "Advanced security options"
   - Under "App passwords", verify you created one
   - Try creating a NEW app password and update .env

3. WAIT A FEW MINUTES:
   - Changes can take 5-15 minutes to propagate
   - Wait, then try again

4. CHECK ACCOUNT TYPE:
   - Personal Outlook accounts: Should work with app passwords
   - Work/School accounts: Might need different setup
   - Is this a work/school account? (If yes, that's the issue)

5. ALTERNATIVE: Use POP3 instead of IMAP:
   - Enable POP in Outlook settings
   - Use pop-mail.outlook.com:995

6. LAST RESORT: Manual email processing
   - We can process emails manually without IMAP
   - Copy/paste email content into the system
""")
