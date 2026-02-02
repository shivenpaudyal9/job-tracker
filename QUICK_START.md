# Job Tracker - Quick Start Guide

Get your Job Tracker website running in 5 minutes! 🚀

---

## Step 1: Start the Backend (2 minutes)

```bash
# Open Terminal 1
cd /c/Users/91953/job-tracker-v2/backend

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ **Backend running at:** http://localhost:8000
📚 **API docs at:** http://localhost:8000/docs

**Leave this terminal running!**

---

## Step 2: Start the Frontend (2 minutes)

```bash
# Open Terminal 2 (new terminal window)
cd /c/Users/91953/job-tracker-v2/frontend

# Install dependencies (first time only)
npm install

# Start the frontend server
npm run dev
```

✅ **Frontend running at:** http://localhost:3000

**Leave this terminal running!**

---

## Step 3: Open the Website (1 minute)

1. **Open your browser** and go to: **http://localhost:3000**

2. **You'll see the landing page** with:
   - Animated hero section
   - "Get Started" button

3. **Click "Get Started"** or **"Go to Dashboard"** (if already connected)

---

## Step 4: Connect Outlook (If First Time)

### You'll see the Setup Wizard:

**Step 1: Connect Outlook**
1. Click **"Start Connection"**
2. A device code will appear (e.g., `ABC123XY`)
3. Click **"Open Microsoft Login"** (opens microsoft.com/devicelogin)
4. Enter the code
5. Sign in with **your own Outlook/Microsoft account**
6. Grant permissions
7. Wait for "Successfully connected!" ✅

**Step 2: Run First Sync**
1. Click **"Start Sync"**
2. Wait 30-60 seconds
3. See count of emails and applications

**Step 3: Complete!**
1. Click **"Go to Dashboard"**

---

## Step 5: Use the Dashboard

### Main Features:

**Stats Cards** (Top)
- Total Applications
- Pending Actions
- Manual Reviews
- Success Rate

**Search & Filters**
- Search by company or job title
- Filter by status (Applied, Interview, Rejected, etc.)
- Filter by action required
- Toggle Grid/List view

**Actions**
- **Sync Now** - Fetch new emails (blue button, top right)
- **Export** - Download Excel file
- **Reviews** - Handle manual reviews (if any)

**Click any application** to view full details

---

## 🎯 Daily Workflow

1. **Open:** http://localhost:3000/dashboard
2. **Click "Sync Now"** to fetch new emails
3. **Review applications** - check status, actions
4. **Handle alerts** - interviews, assessments, deadlines
5. **Export to Excel** when needed

---

## 🐛 Quick Troubleshooting

### Backend won't start?
```bash
cd backend
pip install -r requirements.txt
# Try again
```

### Frontend won't start?
```bash
cd frontend
rm -rf node_modules
npm install
# Try again
```

### "Connection refused" error?
- Make sure backend is running on port 8000
- Check Terminal 1 for errors

### Authentication fails?
- Check `.env` file has correct credentials
- Try deleting `.token_cache.bin` and re-authenticate

### No emails after sync?
- Check you have job emails in Outlook
- Try increasing days back (30 is default)

---

## 📱 Pages You Can Visit

1. **Landing:** http://localhost:3000
2. **Setup:** http://localhost:3000/setup
3. **Dashboard:** http://localhost:3000/dashboard
4. **Manual Review:** http://localhost:3000/manual-review
5. **Application Detail:** http://localhost:3000/applications/1 (after you have data)

---

## 🎨 What You'll See

### Landing Page
- Animated hero with gradient text
- Feature cards with icons
- "How It Works" section
- Stats showcase

### Dashboard
- 4 stat cards at top
- Search bar and filters
- Grid of application cards
- Or table view (toggle)
- Blue "Sync Now" button (top right)

### Each Application Card Shows:
- Company name (bold)
- Job title
- Status badge (colored)
- Confidence percentage
- Location
- Date applied

---

## 💡 Pro Tips

1. **Sync regularly** - Click "Sync Now" daily to stay updated
2. **Use filters** - Find specific applications quickly
3. **Check manual reviews** - Low-confidence items need review
4. **Export often** - Download Excel for offline tracking
5. **Watch action items** - Don't miss deadlines!

---

## 🔥 Cool Features to Try

1. **Grid/List Toggle** - Click the icon buttons (top right of filters)
2. **Search** - Type company name or job title
3. **Status Filter** - See only "Interview Scheduled" items
4. **Action Required** - Filter applications needing your attention
5. **Excel Export** - Download formatted spreadsheet
6. **Real-time Sync** - Watch the spinner when syncing!

---

## 🎉 You're All Set!

Your Job Tracker is now running. Enjoy automatic job application tracking! 🚀

**Questions?** Check README.md for detailed documentation.

**Issues?** See TROUBLESHOOTING section in README.md.
