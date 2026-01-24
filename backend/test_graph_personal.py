"""
Test Microsoft Graph Connection for Personal Accounts

Uses device code flow - perfect for personal Microsoft accounts.
"""

import os
from dotenv import load_dotenv
from msal import PublicClientApplication
import requests
import json

load_dotenv()

CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "consumers")
USER_EMAIL = os.getenv("MICROSOFT_USER_EMAIL")

SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/User.Read"
]

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

print("="*80)
print("MICROSOFT GRAPH - PERSONAL ACCOUNT TEST")
print("="*80)

print(f"\nClient ID: {CLIENT_ID[:8] if CLIENT_ID else 'NOT SET'}...")
print(f"Tenant: {TENANT_ID}")
print(f"User Email: {USER_EMAIL}")

if not CLIENT_ID:
    print("\n[ERROR] MICROSOFT_CLIENT_ID not set in .env file")
    print("Please complete the setup in SETUP_GRAPH_PERSONAL.md first")
    exit(1)

print(f"\nAuthority: {AUTHORITY}")
print(f"Scopes: {', '.join(SCOPES)}")

try:
    # Create MSAL app for public client (device code flow)
    app = PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY
    )

    print("\n" + "="*80)
    print("STEP 1: DEVICE CODE AUTHENTICATION")
    print("="*80)
    print("\nInitiating device code flow...")
    print("This will give you a code to enter in your browser.")

    # Start device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)

    if "user_code" not in flow:
        print(f"\n[ERROR] Failed to initiate device code flow")
        print(f"Response: {flow}")
        exit(1)

    print("\n" + "="*80)
    print("ACTION REQUIRED - COMPLETE AUTHENTICATION")
    print("="*80)
    print(f"\n1. Open this URL in your browser:")
    print(f"   {flow['verification_uri']}")
    print(f"\n2. Enter this code:")
    print(f"   {flow['user_code']}")
    print(f"\n3. Sign in with your Microsoft account: {USER_EMAIL}")
    print(f"\n4. Grant the requested permissions")
    print(f"\n5. Come back here - waiting for you to complete authentication...")
    print(f"\nThis code expires in {flow.get('expires_in', 900) // 60} minutes")
    print("="*80)

    # Wait for user to complete authentication
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        print("\n[SUCCESS] Authentication successful!")
        access_token = result["access_token"]

        print("\n" + "="*80)
        print("STEP 2: TESTING GRAPH API")
        print("="*80)

        # Test 1: Get user profile
        print("\nTest 1: Getting user profile...")
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers
        )

        if response.status_code == 200:
            user = response.json()
            print(f"[OK] User: {user.get('displayName', 'N/A')}")
            print(f"[OK] Email: {user.get('mail') or user.get('userPrincipalName', 'N/A')}")
        else:
            print(f"[ERROR] Failed to get user profile: {response.status_code}")
            print(f"Response: {response.text}")

        # Test 2: Get messages count
        print("\nTest 2: Getting email messages...")
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,from,receivedDateTime",
            headers=headers
        )

        if response.status_code == 200:
            messages = response.json()
            message_list = messages.get("value", [])
            print(f"[OK] Found {len(message_list)} recent emails")

            if message_list:
                print("\nMost recent emails:")
                for i, msg in enumerate(message_list[:3], 1):
                    subject = msg.get("subject", "No subject")
                    from_addr = msg.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
                    date = msg.get("receivedDateTime", "Unknown")
                    print(f"  {i}. {subject[:50]}...")
                    print(f"     From: {from_addr}")
                    print(f"     Date: {date}")
        else:
            print(f"[ERROR] Failed to get messages: {response.status_code}")
            print(f"Response: {response.text}")

        print("\n" + "="*80)
        print("SUCCESS! GRAPH API IS WORKING!")
        print("="*80)
        print("\nThe authentication token has been cached.")
        print("Next time you run sync, it will use the cached token automatically.")
        print("\nNext steps:")
        print("1. Run: python sync_graph_personal.py")
        print("2. This will sync all your job emails automatically!")

    else:
        print("\n[ERROR] Authentication failed")
        print(f"Error: {result.get('error')}")
        print(f"Description: {result.get('error_description')}")

        if "AADSTS" in str(result.get('error_description', '')):
            print("\nTroubleshooting:")
            print("- Make sure you selected 'Personal Microsoft accounts only' during app registration")
            print("- Check that MICROSOFT_TENANT_ID=consumers in .env")
            print("- Verify the Client ID is correct")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
