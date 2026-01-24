# IMAP Email Sync Setup (Personal Outlook Accounts)

## Why IMAP Instead of Microsoft Graph?

For **personal Microsoft accounts**, IMAP is:
- ✅ **Much simpler** - No Azure Portal needed
- ✅ **More reliable** - No tenant issues
- ✅ **Just works** - 5-minute setup
- ✅ **Free forever** - No limits

---

## Step 1: Enable IMAP in Outlook (2 minutes)

1. **Go to:** https://outlook.live.com/mail/0/options/mail/sync
   - Or: Outlook.com → Settings (gear icon) → View all Outlook settings → Mail → Sync email

2. **Enable IMAP:**
   - Under "POP and IMAP", toggle **"Let devices and apps use IMAP"** to **ON**
   - Click **"Save"**

3. **Done!** IMAP is now enabled for your account

---

## Step 2: Generate App-Specific Password (3 minutes)

Microsoft requires app-specific passwords for IMAP (not your regular password).

### Option A: Microsoft Account Security Page

1. **Go to:** https://account.microsoft.com/security

2. **Click:** "Advanced security options"

3. **Scroll to:** "App passwords"

4. **Click:** "Create a new app password"

5. **Copy the password** - It will look like: `abcd efgh ijkl mnop`
   - ⚠️ **Save this immediately!** You can only see it once

### Option B: Direct Link

If you have 2-factor authentication enabled:
- Go to: https://account.live.com/proofs/AppPassword

---

## Step 3: Configure .env File (1 minute)

Add these lines to your `.env` file:

```bash
# IMAP Configuration (for personal Outlook)
OUTLOOK_EMAIL=your.email@outlook.com
OUTLOOK_APP_PASSWORD=abcd efgh ijkl mnop

# Keep existing database config
DATABASE_URL=sqlite:///./jobtracker.db
DEBUG=True
```

**Replace:**
- `your.email@outlook.com` with your actual Outlook email
- `abcd efgh ijkl mnop` with the app password you just created

---

## Step 4: Test Connection (1 minute)

```bash
cd /c/Users/91953/job-tracker-v2/backend
python setup_imap_sync.py
```

**You should see:**
```
Connecting to outlook.office365.com...
[OK] Connected successfully!
Found X emails
```

---

## Step 5: Run Full Sync

Once the test works, sync your emails:

```bash
python setup_imap_sync.py
```

This will:
1. ✅ Connect to your Outlook via IMAP
2. ✅ Fetch emails from last 30 days
3. ✅ Extract company, job title, status, links
4. ✅ Store in database with confidence scores
5. ✅ Route low-confidence items to manual review

---

## What Gets Synced?

The system will process:
- ✅ Application confirmations
- ✅ Rejections
- ✅ Assessment invites
- ✅ Interview requests
- ✅ Offer letters
- ✅ Status updates

It filters out:
- ❌ Spam/marketing emails
- ❌ Non-job-related emails
- ❌ Promotional content

---

## Automated Scheduled Sync

### Option 1: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. **Trigger:** Daily at 8:00 AM
4. **Action:** Start a program
   - **Program:** `python`
   - **Arguments:** `C:\Users\91953\job-tracker-v2\backend\setup_imap_sync.py`
5. Save

### Option 2: Run Manually Daily

Just run whenever you want to sync new emails:
```bash
cd /c/Users/91953/job-tracker-v2/backend
python setup_imap_sync.py
```

---

## Troubleshooting

### Error: "Authentication failed"
- ✓ Check your email is correct in `.env`
- ✓ Make sure you're using the **app password**, not your regular password
- ✓ Verify IMAP is enabled in Outlook settings

### Error: "Connection refused"
- ✓ Check your internet connection
- ✓ Make sure Outlook.com is not blocking IMAP (check security settings)

### Error: "No emails found"
- ✓ Check the date range (`days_back` parameter)
- ✓ Make sure emails are in your Inbox (not Archived/Deleted)

### Emails not being extracted correctly
- ✓ The system is already tuned for your email formats
- ✓ Check confidence scores - low confidence items go to manual review
- ✓ Look at manual review queue: `curl http://127.0.0.1:8000/manual-review`

---

## Advantages Over Microsoft Graph

| Feature | IMAP | Microsoft Graph |
|---------|------|-----------------|
| Setup time | 5 minutes | 15-20 minutes |
| Azure Portal | ❌ Not needed | ✅ Required |
| Personal account support | ✅ Works perfectly | ⚠️ Complex |
| Tenant issues | ❌ None | ✅ Common |
| Rate limits | ❌ None | ✅ Yes (but high) |
| Cost | ✅ Free forever | ✅ Free |

---

## Next Steps

1. ✅ Enable IMAP in Outlook
2. ✅ Generate app password
3. ✅ Update `.env` file
4. ✅ Run `python setup_imap_sync.py`
5. ✅ Export to Excel: `curl -X POST http://127.0.0.1:8000/export`

**Full automation achieved!** 🎉
