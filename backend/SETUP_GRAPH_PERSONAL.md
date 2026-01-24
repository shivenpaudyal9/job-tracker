# Microsoft Graph Setup for Personal Outlook Accounts

## Why This is Different from Before

Last time, we got tenant errors because we didn't configure it correctly for PERSONAL accounts.
This time, we'll do it RIGHT.

---

## Step 1: Register App (5 minutes)

### Go to Azure Portal
**URL:** https://portal.azure.com

**Sign in** with your personal Microsoft account (nkagami19@outlook.com)

### Navigate to App Registrations
1. In the search bar at top, type: **"App registrations"**
2. Click on **"App registrations"** in the results
3. Click **"+ New registration"**

### Register Your App - IMPORTANT SETTINGS

**Name:** `Job Tracker Personal`

**Supported account types:** ⚠️ **THIS IS CRITICAL**
- Select: **"Personal Microsoft accounts only"**
- ❌ NOT "Accounts in this organizational directory only"
- ❌ NOT "Accounts in any organizational directory"
- ✅ **"Personal Microsoft accounts only"**

**Redirect URI:**
- Platform: **Web**
- URL: `http://localhost:8000/callback`

Click **"Register"**

---

## Step 2: Copy Application (Client) ID

After registration, you'll see the Overview page.

**Copy this value:**
- **Application (client) ID**
- Looks like: `12345678-abcd-1234-abcd-123456789abc`

---

## Step 3: Create Client Secret

1. In left sidebar, click **"Certificates & secrets"**
2. Click **"+ New client secret"**
3. **Description:** `Job Tracker Secret`
4. **Expires:** 24 months (or your preference)
5. Click **"Add"**
6. ⚠️ **IMMEDIATELY copy the VALUE** (not the ID!)
   - You can only see it once!
   - Looks like: `abc123~XYZ...`

---

## Step 4: Set API Permissions (DIFFERENT from before!)

1. In left sidebar, click **"API permissions"**
2. Click **"+ Add a permission"**
3. Click **"Microsoft Graph"**
4. Select **"Delegated permissions"** ⚠️ (NOT Application permissions!)

**Add these permissions:**
- `Mail.Read` - Read user mail
- `offline_access` - Maintain access to data
- `User.Read` - Sign in and read user profile

5. Click **"Add permissions"**

**DO NOT click "Grant admin consent"** - not needed for personal accounts with delegated permissions

---

## Step 5: Configure Authentication

1. In left sidebar, click **"Authentication"**
2. Under "Platform configurations", you should see your redirect URI
3. Scroll down to **"Advanced settings"**
4. Under **"Allow public client flows"**:
   - Toggle **"Enable the following mobile and desktop flows"** to **YES**
5. Click **"Save"** at the top

---

## Step 6: Update .env File

Add these to your `.env` file:

```bash
# Microsoft Graph (Personal Account)
MICROSOFT_CLIENT_ID=paste_your_client_id_here
MICROSOFT_CLIENT_SECRET=paste_your_secret_value_here
MICROSOFT_TENANT_ID=consumers
MICROSOFT_USER_EMAIL=nkagami19@outlook.com
```

**Important:** Set `MICROSOFT_TENANT_ID=consumers` (this is special for personal accounts!)

---

## Step 7: Test Connection

We'll use a different authentication flow for personal accounts (device code flow).

Run:
```bash
cd /c/Users/91953/job-tracker-v2/backend
python test_graph_personal.py
```

This will:
1. Show you a code and a URL
2. You open the URL in your browser
3. Enter the code
4. Sign in with your Microsoft account
5. Grant permissions
6. Done! The system will remember your auth

---

## Why This Works for Personal Accounts

**Before:**
- ❌ Used organizational tenant
- ❌ Tried application permissions
- ❌ Got "tenant not found" errors

**Now:**
- ✅ Using "consumers" tenant (for personal accounts)
- ✅ Using delegated permissions (user-based)
- ✅ Using device code flow (no web server needed)
- ✅ Will work perfectly!

---

## Ready to Start?

1. Open: https://portal.azure.com
2. Search for: "App registrations"
3. Click: "+ New registration"
4. Select: "Personal Microsoft accounts only"
5. Tell me when you're done!
