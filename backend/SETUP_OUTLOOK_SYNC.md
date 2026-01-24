# Setting Up Outlook Email Sync

Follow these steps to sync your job application emails from Outlook.

## Step 1: Register Azure App (5 minutes)

1. **Go to Azure Portal**
   - Visit: https://portal.azure.com
   - Sign in with your Microsoft account (same one used for Outlook)

2. **Navigate to App Registrations**
   - Search for "Azure Active Directory" or "Microsoft Entra ID"
   - Click on it
   - In the left sidebar, click **"App registrations"**
   - Click **"+ New registration"**

3. **Register the App**
   - **Name:** `Job Tracker` (or any name you prefer)
   - **Supported account types:** Select **"Accounts in this organizational directory only"**
     - If you're using personal Outlook, select **"Personal Microsoft accounts only"**
   - **Redirect URI:** Leave blank (not needed for this app)
   - Click **"Register"**

---

## Step 2: Copy Client ID and Tenant ID (1 minute)

After registration, you'll see the app overview page:

1. **Copy Application (client) ID**
   - You'll see a field called **"Application (client) ID"**
   - It looks like: `12345678-1234-1234-1234-123456789abc`
   - **Copy this value** - you'll need it for the `.env` file

2. **Copy Directory (tenant) ID**
   - Below the client ID, you'll see **"Directory (tenant) ID"**
   - It also looks like: `87654321-4321-4321-4321-cba987654321`
   - **Copy this value** too

---

## Step 3: Create Client Secret (2 minutes)

1. **Navigate to Certificates & secrets**
   - In the left sidebar of your app, click **"Certificates & secrets"**

2. **Create new secret**
   - Under "Client secrets", click **"+ New client secret"**
   - **Description:** `Job Tracker Secret` (any name)
   - **Expires:** Select **"24 months"** (or your preference)
   - Click **"Add"**

3. **IMPORTANT: Copy the secret VALUE immediately**
   - You'll see a new secret appear with a **"Value"** column
   - **Copy the VALUE** (not the "Secret ID")
   - The value looks like: `abc123XYZ~randomChars.moreChars`
   - ⚠️ **YOU CAN ONLY SEE THIS ONCE!** If you miss it, you'll need to create a new secret.

---

## Step 4: Set API Permissions (3 minutes)

1. **Navigate to API permissions**
   - In the left sidebar, click **"API permissions"**

2. **Add Microsoft Graph permissions**
   - Click **"+ Add a permission"**
   - Select **"Microsoft Graph"**
   - Choose **"Application permissions"** (NOT Delegated)

3. **Add these permissions:**
   - Search for and select **"Mail.Read"**
     - Expand "Mail" → Check **"Mail.Read"**
   - Click **"Add permissions"**

4. **Grant Admin Consent** ⚠️ CRITICAL STEP
   - After adding permissions, click **"Grant admin consent for [Your Organization]"**
   - Click **"Yes"** in the confirmation dialog
   - You should see green checkmarks appear next to the permissions
   - ⚠️ **Without this step, the app cannot access emails!**

---

## Step 5: Update .env File (1 minute)

Now update your `.env` file with the credentials:

```bash
# Database - Using SQLite for quick development
DATABASE_URL=sqlite:///./jobtracker.db

# Microsoft Graph (Outlook Integration)
MICROSOFT_CLIENT_ID=paste_your_client_id_here
MICROSOFT_CLIENT_SECRET=paste_your_client_secret_value_here
MICROSOFT_TENANT_ID=paste_your_tenant_id_here
MICROSOFT_USER_EMAIL=your.outlook@email.com

# Application
DEBUG=True
```

**Replace:**
- `paste_your_client_id_here` with the Application (client) ID from Step 2
- `paste_your_client_secret_value_here` with the secret VALUE from Step 3
- `paste_your_tenant_id_here` with the Directory (tenant) ID from Step 2
- `your.outlook@email.com` with your actual Outlook email address

---

## Step 6: Test the Connection (2 minutes)

Run this test script to verify everything works:

```bash
cd /c/Users/91953/job-tracker-v2/backend
python -c "
from app.graph_client import OutlookGraphClient
import os
from dotenv import load_dotenv

load_dotenv()

print('Testing Microsoft Graph connection...')
print(f'Client ID: {os.getenv(\"MICROSOFT_CLIENT_ID\")[:8]}...')
print(f'Tenant ID: {os.getenv(\"MICROSOFT_TENANT_ID\")[:8]}...')
print(f'User Email: {os.getenv(\"MICROSOFT_USER_EMAIL\")}')

try:
    client = OutlookGraphClient()
    print('✓ Authentication successful!')
    print('Ready to sync emails.')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

---

## Step 7: Sync Your Emails

Once the test passes, sync your emails:

**Option A: Via API**
```bash
curl -X POST http://127.0.0.1:8000/sync?days_back=30
```

**Option B: Via Python**
```bash
python -c "
from app.database import SessionLocal
from app.graph_client import sync_outlook_emails

db = SessionLocal()
result = sync_outlook_emails(db, days_back=30)
print(f'Synced: {result}')
"
```

---

## Troubleshooting

### Error: "AADSTS7000215: Invalid client secret"
- The client secret value is wrong
- Go back to Azure Portal → Certificates & secrets → Create a new secret
- Copy the VALUE immediately and update `.env`

### Error: "Forbidden" or "Insufficient privileges"
- You didn't grant admin consent
- Go to Azure Portal → API permissions → Click "Grant admin consent"
- Make sure you see green checkmarks

### Error: "The tenant for tenant does not exist"
- Wrong Tenant ID
- Go to Azure Portal → Your app → Overview → Copy the Directory (tenant) ID again

### Error: "AADSTS700016: Application not found"
- Wrong Client ID
- Go to Azure Portal → Your app → Overview → Copy the Application (client) ID again

### No emails found
- Check that `MICROSOFT_USER_EMAIL` matches your Outlook email exactly
- Try increasing `days_back` parameter (e.g., 90 days)
- Verify emails are in your Outlook inbox (not archived/deleted)

---

## What Happens During Sync

1. **Authenticates** with Microsoft Graph using your credentials
2. **Fetches emails** from your Outlook inbox (last 30 days by default)
3. **Filters** for job-related emails (application confirmations, rejections, etc.)
4. **Unwraps** forwarded email content (extracts original sender)
5. **Extracts** company name, job title, status, actions, links
6. **Matches** to existing applications or creates new ones
7. **Stores** everything in database with confidence scores
8. **Routes** low-confidence items to manual review queue

---

## Next Steps After Sync

1. **Check stats**: `curl http://127.0.0.1:8000/stats`
2. **View applications**: Visit http://127.0.0.1:8000/docs
3. **Manual review**: `curl http://127.0.0.1:8000/manual-review`
4. **Export to Excel**: `curl -X POST http://127.0.0.1:8000/export`

---

## Important Notes

- **Personal vs Work Account:** If you're using a personal Outlook account (@outlook.com, @hotmail.com), select "Personal Microsoft accounts only" during app registration
- **Security:** Keep your client secret safe - don't commit it to Git
- **Rate Limits:** Microsoft Graph has rate limits - the sync automatically handles this
- **Incremental Sync:** After the first sync, subsequent syncs only fetch new emails (uses delta queries)

---

Ready to start? Follow Step 1 and I'll guide you through each step!
