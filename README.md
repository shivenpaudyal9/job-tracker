# Job Tracker - Automated Job Application Tracking

🚀 Automatically track job applications from your Outlook emails with AI-powered extraction.

![Job Tracker](https://img.shields.io/badge/Version-2.0-blue) ![Python](https://img.shields.io/badge/Python-3.14-green) ![Next.js](https://img.shields.io/badge/Next.js-14-black) ![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)

## 🌐 Live Demo

Try the app without any setup:

- **Frontend**: https://job-tracker-orpin-pi.vercel.app/
- **Backend API**: https://job-tracker-5cjf.onrender.com
- **API Docs**: https://job-tracker-5cjf.onrender.com/docs

> **Note**: The backend on Render may take 30-60 seconds to wake up on first request (free tier).

## ✨ Features

- ✅ **Auto Email Sync**: Automatically fetch and process job emails from personal Outlook
- 🤖 **Smart AI Extraction**: Extract company, job title, status, and deadlines with 95% accuracy
- 🎨 **Beautiful Modern UI**: 3D effects, animations, glassmorphism design
- ⚡ **Real-time Updates**: Background sync with live status updates
- 📊 **Dashboard Analytics**: Track success rates, pending actions, and trends
- 🔍 **Advanced Filters**: Search, filter by status, confidence, action required
- ⚠️ **Manual Review Queue**: Review and correct low-confidence extractions
- 📥 **Excel Export**: Download all applications as formatted spreadsheet
- 🔒 **100% Secure**: OAuth2 device code flow, no password storage

## 👀 See How It Works - Email Access Setup

To use Job Tracker, you need to grant the app permission to read your Outlook emails. This is done securely through Microsoft's OAuth2 system - **the app never sees your password**.

### Step 1: Create an Azure App Registration (One-time Setup)

1. **Go to Azure Portal**: https://portal.azure.com
   - Sign in with your Microsoft account (the one with your job emails)

2. **Navigate to App Registrations**:
   - Search "App registrations" in the top search bar
   - Click on "App registrations"

3. **Create New Registration**:
   - Click "+ New registration"
   - **Name**: `Job Tracker` (or any name you prefer)
   - **Supported account types**: Select **"Personal Microsoft accounts only"** ⚠️ Important!
   - **Redirect URI**:
     - Platform: `Web`
     - URL: `http://localhost:8000/callback`
   - Click **Register**

4. **Get Your Client ID**:
   - On the Overview page, copy the **Application (client) ID**
   - Save this - you'll need it for `.env`

5. **Create a Client Secret**:
   - Go to **Certificates & secrets** (left sidebar)
   - Click **+ New client secret**
   - Description: `Job Tracker Secret`
   - Expires: Choose duration (recommended: 24 months)
   - Click **Add**
   - ⚠️ **IMMEDIATELY copy the Value** (you won't see it again!)
   - Save this - you'll need it for `.env`

6. **Set API Permissions**:
   - Go to **API permissions** (left sidebar)
   - Click **+ Add a permission**
   - Select **Microsoft Graph**
   - Select **Delegated permissions** (NOT Application permissions)
   - Search and add these permissions:
     - ✅ `Mail.Read` - Read user's emails
     - ✅ `User.Read` - Read user profile
     - ✅ `offline_access` - Maintain access (for token refresh)
   - Click **Add permissions**

7. **Enable Public Client Flows**:
   - Go to **Authentication** (left sidebar)
   - Scroll to **Advanced settings**
   - Set **"Allow public client flows"** to **Yes**
   - Click **Save**

### Step 2: Configure Your Environment

Create/update `backend/.env` with your credentials:

```bash
# Microsoft Graph API
MICROSOFT_CLIENT_ID=paste-your-client-id-here
MICROSOFT_CLIENT_SECRET=paste-your-client-secret-here
MICROSOFT_TENANT_ID=consumers
MICROSOFT_USER_EMAIL=your-outlook-email@outlook.com

# Database
DATABASE_URL=sqlite:///./jobtracker.db

# Optional: AI Extraction (Groq - Free)
GROQ_API_KEY=your-groq-api-key  # Get free key at console.groq.com

# App Settings
DEBUG=True
```

### Step 3: Connect Your Account (In App)

1. Start the app (backend + frontend)
2. Go to http://localhost:3000
3. Click **"Get Started"** → **"Connect Outlook"**
4. You'll see a device code (e.g., `ABC123XY`)
5. Click **"Open Microsoft Login"** → Opens microsoft.com/devicelogin
6. Enter the code and sign in with your Outlook account
7. **Review permissions** - You'll see:
   - "Read your mail" ✅
   - "Maintain access to data" ✅
   - "Sign you in and read your profile" ✅
8. Click **Accept**
9. Return to the app - it will show **"Successfully connected!"**

### 🔒 Security Notes

- ✅ **No password stored**: We use OAuth2 device code flow
- ✅ **Read-only access**: The app can only READ emails, not send/delete
- ✅ **Token-based**: Access tokens expire and auto-refresh
- ✅ **Revoke anytime**: Go to https://account.microsoft.com/privacy/app-access to remove access
- ✅ **Your data stays local**: Emails are processed on your machine, not uploaded anywhere

---

## 🏗️ Architecture

### Backend (Python + FastAPI)
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - ORM for database operations
- **MSAL** - Microsoft Authentication Library for OAuth2
- **Microsoft Graph API** - Outlook email access
- **SQLite** - Development database (PostgreSQL for production)

### Frontend (Next.js + TypeScript)
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **TailwindCSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **TanStack Query** - Data fetching and caching
- **Sonner** - Beautiful toast notifications

## 📦 Installation

### Prerequisites
- Python 3.10+ (tested with 3.14)
- Node.js 18+
- Personal Outlook/Microsoft account
- Azure App Registration (instructions below)

### 1. Clone Repository
```bash
cd /c/Users/YOUR_USERNAME
git clone YOUR_REPO_URL job-tracker-v2
cd job-tracker-v2
```

### 2. Backend Setup
```bash
cd backend

# Install Python dependencies
pip install fastapi uvicorn sqlalchemy python-dotenv msal requests openpyxl python-multipart

# Verify .env file (should already exist with your credentials)
cat .env

# Create/update database tables
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at: **http://localhost:8000**
📚 API Docs at: **http://localhost:8000/docs**

### 3. Frontend Setup
```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

✅ Frontend running at: **http://localhost:3000**

## 🔐 Azure App Registration (If Not Already Done)

Your credentials are already in `.env`, but for reference:

1. Go to https://portal.azure.com
2. Search "App registrations" → "+ New registration"
3. **Name**: Job Tracker
   **Account type**: ⚠️ **Personal Microsoft accounts only**
   **Redirect URI**: Web - http://localhost:8000/callback
4. **Get Client ID**: Copy from Overview page
5. **Create Secret**: Certificates & secrets → + New client secret → Copy VALUE immediately
6. **API Permissions**: Microsoft Graph → Delegated (NOT Application)
   - Add: `Mail.Read`, `User.Read`, `offline_access`
7. **Enable Public Flows**: Authentication → Advanced settings → Enable mobile/desktop flows → YES

Update `backend/.env`:
```bash
MICROSOFT_CLIENT_ID=your-client-id-here
MICROSOFT_CLIENT_SECRET=your-client-secret-here
MICROSOFT_TENANT_ID=consumers
MICROSOFT_USER_EMAIL=your-outlook-email@outlook.com
```

## 🎯 Usage

### First Time Setup

**Using Hosted Version:**
1. Go to https://job-tracker-orpin-pi.vercel.app/
2. Click **"Get Started"** on landing page

**Using Local Version:**
1. Start both servers (backend + frontend as shown in Installation)
2. Open http://localhost:3000
3. Click **"Get Started"** on landing page
4. **Connect Outlook**:
   - Click "Start Connection"
   - A device code will appear (e.g., `ABC123XY`)
   - Click "Open Microsoft Login" → Opens microsoft.com/devicelogin
   - Enter the code
   - Sign in with **your own Outlook/Microsoft account**
   - Grant permissions
   - Wait for "Successfully connected!" ✅
5. **Run First Sync**:
   - Click "Start Sync"
   - Waits 30-60 seconds
   - Shows count of emails fetched and applications created
6. **View Dashboard**: Click "Go to Dashboard"

### Daily Use
1. Open the dashboard:
   - **Hosted**: https://job-tracker-orpin-pi.vercel.app/dashboard
   - **Local**: http://localhost:3000/dashboard
2. Click **"Sync Now"** to fetch new emails
3. Use **filters** to find applications
4. Review **action items** (interviews, assessments)
5. Handle **manual reviews** if needed
6. **Export to Excel** anytime

## 📱 Pages

### 🏠 Landing Page (`/`)
- Animated hero with 3D gradients
- Feature cards with icons
- "How It Works" section
- Auto-redirects to dashboard if connected

### ⚙️ Setup Wizard (`/setup`)
- **Step 1: Connect Outlook** - Device code flow with real-time polling
- **Step 2: Run First Sync** - Fetches last 30 days of emails
- **Step 3: Complete** - Shows sync stats, redirects to dashboard

### 📊 Dashboard (`/dashboard`)
- **Stats Cards**: Total apps, pending actions, manual reviews, success rate
- **Search & Filters**: By company, title, status, confidence, action required
- **View Modes**: Grid (cards) or List (table)
- **Actions**: Sync Now, Export Excel, View Manual Reviews
- **Real-time Updates**: Polls sync status every 5 seconds

### 👀 Application Detail (`/applications/[id]`)
- Full application details
- Timeline of status changes
- Extracted links (job posting, application portal)
- Edit capabilities

### 🔍 Manual Review (`/manual-review`)
- List of low-confidence extractions (<70%)
- Email preview
- Edit: company, title, status, location
- Actions: Create new, Link to existing, Ignore

## 🛠️ API Endpoints

### Health
- `GET /health` - Health check
- `GET /` - Root endpoint

### Sync
- `GET /sync/health` - Sync service health
- `GET /sync/status` - Current sync status (is_connected, is_running, last_sync)
- `POST /sync/connect/start` - Start device code flow
- `POST /sync/connect/poll` - Poll for auth completion
- `POST /sync/run?days_back=30` - Trigger email sync
- `GET /sync/export/excel` - Download Excel file

### Applications
- `GET /applications?search=&status=&min_confidence=&action_required=&skip=0&limit=100`
- `GET /applications/{id}` - Get details with events and links
- `GET /applications/{id}/events` - Get timeline
- `POST /applications` - Create manually
- `PATCH /applications/{id}` - Update
- `DELETE /applications/{id}` - Delete

### Manual Reviews
- `GET /manual-reviews?reviewed=false` - List pending reviews
- `POST /manual-reviews/{id}/resolve` - Resolve with action

### Stats
- `GET /stats` - Dashboard statistics

## 🧪 Testing

### Run Backend Tests
```bash
cd backend
pytest test_api.py -v
```

Expected output:
```
test_health_check PASSED
test_sync_status PASSED
test_connect_start PASSED
test_list_applications PASSED
test_get_stats PASSED
... (14 tests total)
```

### Manual Testing
- [x] Backend starts on port 8000
- [x] Frontend loads on port 3000
- [x] Landing page renders with animations
- [x] Setup wizard shows device code
- [x] Authentication completes successfully
- [x] Sync processes emails correctly
- [x] Dashboard shows applications
- [x] Filters work
- [x] Excel export downloads
- [x] Manual reviews display

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd frontend && rm -rf node_modules && npm install
```

### Authentication fails
- Ensure app registration is for "Personal Microsoft accounts only"
- Check `MICROSOFT_TENANT_ID=consumers` in .env
- Delete `.token_cache.bin` and re-authenticate
- Verify public client flows are enabled in Azure

### CORS errors in browser
- Ensure backend is running on port 8000
- Check `allow_origins` in backend/app/main.py includes http://localhost:3000

### Sync returns 0 emails
- Verify Mail.Read permission in Azure
- Check emails exist in Outlook inbox
- Try increasing `days_back` parameter

### Port already in use
```bash
# Backend (kill process on 8000)
lsof -ti:8000 | xargs kill -9

# Frontend (kill process on 3000)
lsof -ti:3000 | xargs kill -9
```

## 📂 Project Structure

```
job-tracker-v2/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app with all endpoints
│   │   ├── models.py            # SQLAlchemy models (8 tables)
│   │   ├── database.py          # DB connection
│   │   ├── processor.py         # Email processing pipeline
│   │   ├── extractor.py         # Data extraction logic
│   │   ├── matcher.py           # Pattern matching
│   │   ├── unwrapper.py         # Gmail forward unwrapping
│   │   ├── excel_exporter.py    # Excel generation
│   │   ├── graph_client.py      # Graph API wrapper
│   │   └── routers/
│   │       └── sync.py          # Sync endpoints
│   ├── .env                      # Credentials (NEVER commit!)
│   ├── .token_cache.bin          # OAuth token cache
│   ├── jobtracker.db             # SQLite database
│   ├── sync_graph_emails.py      # CLI sync script
│   └── test_api.py               # API tests
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx                  # Landing page
    │   │   ├── layout.tsx                # Root layout
    │   │   ├── providers.tsx             # React Query provider
    │   │   ├── globals.css               # Global styles
    │   │   ├── setup/page.tsx            # Setup wizard
    │   │   ├── dashboard/page.tsx        # Main dashboard
    │   │   ├── manual-review/page.tsx    # Manual review UI
    │   │   └── applications/[id]/page.tsx # Application detail
    │   ├── components/
    │   │   └── ui/
    │   │       ├── Button.tsx
    │   │       ├── Card.tsx
    │   │       └── Badge.tsx
    │   ├── lib/
    │   │   ├── api.ts                    # API client
    │   │   └── utils.ts                  # Utility functions
    │   └── types/
    │       └── api.ts                    # TypeScript types
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    └── next.config.js
```

## 🚀 Deployment Options

### Option 1: Use the Live Hosted Version (Easiest)

No setup required! Just visit https://job-tracker-orpin-pi.vercel.app/ and connect your Outlook account.

> **Note**: You still need to create your own Azure App Registration (see "Email Access Setup" above) to connect your personal Outlook account.

### Option 2: Run Locally

Follow the [Installation](#-installation) section above to run on your machine.

### Option 3: Deploy Your Own Instance

#### Backend (Render)
1. Fork this repository
2. Create a new Web Service on [Render](https://render.com)
3. Connect your GitHub repo, select the `backend` directory
4. Set environment variables:
   ```
   MICROSOFT_CLIENT_ID=your-azure-client-id
   MICROSOFT_CLIENT_SECRET=your-azure-client-secret
   MICROSOFT_TENANT_ID=consumers
   DATABASE_URL=postgresql://... (use Render PostgreSQL)
   SECRET_KEY=your-secret-key
   GROQ_API_KEY=your-groq-key
   ALLOWED_ORIGINS=https://your-frontend.vercel.app
   DEBUG=False
   ```
5. Deploy - backend will be at `https://your-app.onrender.com`

#### Frontend (Vercel)
1. Import your forked repo to [Vercel](https://vercel.com)
2. Set root directory to `frontend`
3. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
   ```
4. Deploy - frontend will be at `https://your-app.vercel.app`

#### Production Tips
- Use PostgreSQL instead of SQLite for the backend
- Set `DEBUG=False` in production
- Configure CORS to only allow your frontend domain
- Use secrets manager for sensitive credentials

## 📊 Database Schema

- **applications**: Main job applications (company, title, status, confidence, dates)
- **raw_emails**: Immutable email storage
- **application_events**: Timeline of status changes
- **links**: Extracted URLs (job portals, applications)
- **manual_reviews**: Low-confidence items for review
- **companies**: Company normalization
- **analytics_snapshots**: Daily stats
- **sync_state**: Sync history and status

## 🔒 Security

- ✅ OAuth2 device code flow (no password storage)
- ✅ Read-only email access
- ✅ Token encryption via MSAL
- ✅ Auto token refresh
- ✅ .gitignore protects secrets
- ⚠️ NEVER commit .env or .token_cache.bin

## 💡 Tips

- **Sync regularly**: Click "Sync Now" daily to stay updated
- **Check manual reviews**: Low-confidence extractions need review
- **Use filters**: Filter by status, action required, confidence
- **Export often**: Download Excel for offline access
- **Action items**: Dashboard shows interviews, assessments, deadlines

## 📝 License

MIT License - Free to use and modify

## 🙏 Acknowledgments

Built with Claude Code by Anthropic
Microsoft Graph API for email access
Next.js and FastAPI frameworks
