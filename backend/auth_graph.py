"""Quick Microsoft Graph Authentication"""
import os
import sys
from dotenv import load_dotenv
from msal import PublicClientApplication

load_dotenv()

CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
SCOPES = ["https://graph.microsoft.com/Mail.Read", "https://graph.microsoft.com/User.Read"]

app = PublicClientApplication(
    client_id=CLIENT_ID,
    authority="https://login.microsoftonline.com/consumers"
)

print("Generating device code...")
sys.stdout.flush()

flow = app.initiate_device_flow(scopes=SCOPES)

print(f"\n{'='*80}")
print("AUTHENTICATION REQUIRED")
print(f"{'='*80}")
print(f"\n1. Open: {flow['verification_uri']}")
print(f"\n2. Enter code: {flow['user_code']}")
print(f"\n3. Sign in with your Outlook/Microsoft account")
print(f"\n{'='*80}")
print(f"Waiting for you to complete authentication (expires in {flow.get('expires_in', 900) // 60} min)...")
sys.stdout.flush()

result = app.acquire_token_by_device_flow(flow)

if "access_token" in result:
    print("\nSUCCESS! Authentication complete!")
else:
    print(f"\nFailed: {result.get('error_description')}")
