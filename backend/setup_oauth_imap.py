"""
OAuth2 IMAP Setup for Outlook

Microsoft has blocked Basic Auth (app passwords) for many accounts.
This uses OAuth2 instead - the modern authentication method.
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("="*80)
print("OUTLOOK OAUTH2 SETUP")
print("="*80)

print("""
PROBLEM IDENTIFIED:
Your Outlook account has Basic Authentication BLOCKED.
Error: "BasicAuthBlocked"

Microsoft is disabling app password authentication for personal accounts.
You need to use OAuth2 instead.

SOLUTION - 2 Options:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPTION 1: Use Microsoft Graph API (RECOMMENDED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is what we tried earlier in Azure Portal. For PERSONAL accounts,
there's a simpler way:

1. Register app at: https://apps.dev.microsoft.com
   (This is easier than Azure Portal for personal accounts)

2. Get Client ID and Secret

3. Use Microsoft Graph to read emails (no IMAP needed!)

Benefits:
  ✓ Works with personal accounts
  ✓ No Basic Auth issues
  ✓ More reliable
  ✓ Better rate limits

Setup time: ~10 minutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPTION 2: Enable Basic Auth (If Possible)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Some accounts allow re-enabling Basic Auth:

1. Go to: https://outlook.live.com/mail/0/options/mail/sync

2. Look for "Authenticated SMTP" or "Let devices and apps use POP and IMAP"

3. Make sure ALL these are ON:
   - Let devices and apps use IMAP
   - Let devices and apps use POP
   - Authenticated SMTP

4. Also check: https://account.microsoft.com/security
   - Look for any "Security defaults" or "Modern authentication" settings
   - Try to disable if you see them

Note: Microsoft is phasing this out, so it might not work.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPTION 3: Manual Email Processing (WORKS NOW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The system is ALREADY WORKING with manual processing!

You saw it extract:
  • Eleven Recruiting - Workday Reporting Analyst
  • 90% company confidence, 75% job title confidence
  • Status: APPLIED_RECEIVED

You can:
  1. Copy/paste emails into the system
  2. Forward emails to yourself, save them, process them
  3. Use the API to add applications manually

This works TODAY while we set up automation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATION:

For full automation, I recommend Option 1 (Microsoft Graph).
It's the modern approach and designed for personal accounts.

Want me to guide you through Microsoft Graph setup?
It's actually simpler than what we tried before.
""")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print("\nWhich option do you want?")
print("1. Set up Microsoft Graph (10 min, full automation)")
print("2. Try to enable Basic Auth (may not work)")
print("3. Continue with manual processing (works now)")
