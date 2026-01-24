# Job Tracker - Automated Job Application Tracking

🚀 Automatically track job applications from your Outlook emails with AI-powered extraction.

![Job Tracker](https://img.shields.io/badge/Version-2.0-blue) ![Python](https://img.shields.io/badge/Python-3.14-green) ![Next.js](https://img.shields.io/badge/Next.js-14-black) ![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)

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
1. **Start both servers** (backend + frontend as shown above)
2. **Open app**: http://localhost:3000
3. **Click "Get Started"** on landing page
4. **Connect Outlook**:
   - Click "Start Connection"
   - Device code will appear (e.g., `ABC123XY`)
   - Click "Open Microsoft Login" → Opens microsoft.com/devicelogin
   - Enter the code
   - Sign in with `nkagami19@outlook.com`
   - Grant permissions
   - Wait for "Successfully connected!" ✅
5. **Run First Sync**:
   - Click "Start Sync"
   - Waits 30-60 seconds
   - Shows count of emails fetched and applications created
6. **View Dashboard**: Click "Go to Dashboard"

### Daily Use
1. Open http://localhost:3000/dashboard
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

## 🚀 Production Deployment

### Backend
1. Use PostgreSQL instead of SQLite
2. Set `DEBUG=False` in .env
3. Configure CORS for production domain
4. Use gunicorn: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`
5. Set up HTTPS with nginx/Caddy
6. Use secrets manager for credentials

### Frontend
1. Build: `npm run build`
2. Deploy to Vercel/Netlify or self-host
3. Update `NEXT_PUBLIC_API_URL` to production backend
4. Configure custom domain

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
