# Deployment Guide (100% Free)

Deploy your Job Tracker for **$0/month** using Render + Neon + Vercel.

## Architecture Overview

- **Backend**: FastAPI (Python) - Deployed to **Render** (free)
- **Database**: PostgreSQL - Hosted on **Neon** (free, 500MB)
- **Frontend**: Next.js - Deployed to **Vercel** (free)

## Prerequisites

1. [GitHub account](https://github.com/) - for code hosting
2. [Render account](https://render.com/) - for backend hosting (free)
3. [Neon account](https://neon.tech/) - for PostgreSQL database (free)
4. [Vercel account](https://vercel.com/) - for frontend hosting (free)
5. [Azure account](https://portal.azure.com/) - for Microsoft Graph API (free)

---

## Step 1: Push Code to GitHub

```bash
cd job-tracker-v2
git init
git add .
git commit -m "Initial commit - Multi-user Job Tracker"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/job-tracker.git
git push -u origin main
```

---

## Step 2: Create Free PostgreSQL Database (Neon)

### 2.1 Create Neon Account & Project

1. Go to [Neon Console](https://console.neon.tech/)
2. Sign up (free) and create a new project
3. Name it `job-tracker`
4. Select a region close to you

### 2.2 Get Connection String

1. In your Neon dashboard, click on your project
2. Go to **Connection Details**
3. Copy the **Connection string** (starts with `postgresql://`)
4. Save this - you'll need it for Render

Example: `postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

---

## Step 3: Deploy Backend to Render (Free)

### 3.1 Create Render Account & Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** > **"Web Service"**
3. Connect your GitHub account
4. Select your `job-tracker` repository
5. Configure:
   - **Name**: `job-tracker-api`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**

### 3.2 Configure Environment Variables

In Render, go to **Environment** tab and add:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Your Neon connection string |
| `JWT_SECRET_KEY` | Generate one (see below) |
| `MICROSOFT_CLIENT_ID` | Your Azure App Client ID |
| `MICROSOFT_TENANT_ID` | `consumers` |
| `ALLOWED_ORIGINS` | `http://localhost:3000` (update after Vercel deploy) |
| `DEBUG` | `False` |

**Generate JWT Secret** (run in terminal):
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.3 Deploy

Click **"Create Web Service"**. Render will deploy automatically.

Your backend URL will be: `https://job-tracker-api.onrender.com`

> **Note**: Free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

---

## Step 4: Deploy Frontend to Vercel (Free)

### 4.1 Create Vercel Project

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"Add New"** > **"Project"**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`

### 4.2 Configure Environment Variables

Before deploying, add environment variable:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://job-tracker-api.onrender.com` |

### 4.3 Deploy

Click **"Deploy"**. Your frontend URL will be: `https://job-tracker-xxx.vercel.app`

---

## Step 5: Update CORS on Render

Go back to Render > your service > Environment, and update:

```
ALLOWED_ORIGINS=http://localhost:3000,https://job-tracker-xxx.vercel.app
```

Click **"Save Changes"** - Render will redeploy automatically.

---

## Step 6: Configure Microsoft Azure (for Outlook sync)

### 6.1 Create/Update App Registration

1. Go to [Azure Portal](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Create new or select existing App Registration
3. Go to **Authentication** > **Add a platform** > **Mobile and desktop applications**
4. Add redirect URI: `https://login.microsoftonline.com/common/oauth2/nativeclient`
5. Enable **"Allow public client flows"** = Yes

### 6.2 Get Client ID

1. Go to **Overview**
2. Copy **Application (client) ID**
3. This is your `MICROSOFT_CLIENT_ID`

---

## Final Checklist

- [ ] Neon database created
- [ ] Render backend deployed with all env variables
- [ ] Vercel frontend deployed with `NEXT_PUBLIC_API_URL`
- [ ] CORS updated on Render with Vercel URL
- [ ] Azure App Registration configured

---

## Test Your Deployment

1. Open your Vercel URL: `https://your-app.vercel.app`
2. Click **"Get Started"** > **"Create Account"**
3. Register with email/password
4. Connect your Outlook account
5. Sync your emails!

---

## Environment Variables Reference

### Backend (Render)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Neon PostgreSQL connection string | Yes |
| `JWT_SECRET_KEY` | Secret for JWT tokens (32+ chars) | Yes |
| `MICROSOFT_CLIENT_ID` | Azure App Client ID | Yes |
| `MICROSOFT_TENANT_ID` | `consumers` for personal accounts | Yes |
| `ALLOWED_ORIGINS` | Comma-separated frontend URLs | Yes |
| `DEBUG` | Set to `False` in production | No |

### Frontend (Vercel)

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Render backend URL | Yes |

---

## Troubleshooting

### Backend returns 503 or takes long to respond
- **Cause**: Render free tier sleeps after 15min inactivity
- **Solution**: First request wakes it up (~30s). This is normal for free tier.

### "Could not validate credentials" error
- Check `JWT_SECRET_KEY` is set correctly
- Make sure you're logged in (token expires after 7 days)

### CORS errors in browser
- Add your Vercel URL to `ALLOWED_ORIGINS` on Render
- No trailing slash in URLs
- Redeploy after changing

### Database connection errors
- Check Neon connection string is correct
- Ensure `?sslmode=require` is in the URL

### Outlook sync not working
- Verify `MICROSOFT_CLIENT_ID` matches your Azure app
- Check Azure > Authentication > "Allow public client flows" = Yes
- Each user must connect their own Outlook

---

## Cost Summary

| Service | Plan | Cost | Limits |
|---------|------|------|--------|
| Render | Free | $0 | Sleeps after 15min, 750 hrs/month |
| Neon | Free | $0 | 500MB storage, 1 project |
| Vercel | Hobby | $0 | Unlimited deploys for personal use |
| Azure | Free | $0 | App registration is free |

**Total: $0/month**

---

## Upgrading Later

If you need always-on backend (no sleep):
- **Render Starter**: $7/month
- **Railway**: $5/month

For now, free tier works great for personal/small team use!
