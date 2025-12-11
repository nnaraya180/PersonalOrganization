# Deployment Guide - Render.com

## Overview
This guide will help you deploy your Personal Assistant app to Render with a public URL.

## Pre-Deployment Checklist

✅ **Files Updated:**
- `requirements.txt` - Added all Python dependencies with versions
- `render.yaml` - Configured both backend and frontend services
- `backend/main.py` - Updated CORS to allow production URLs
- `frontend/src/api.ts` - Uses environment variable for API URL
- `frontend/.env.production` - Production API URL
- `frontend/.env.development` - Local development API URL

## Step 1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub account (recommended)
3. Authorize Render to access your repository

## Step 2: Create a New Web Service (Blueprint)

### Option A: Using render.yaml (Recommended)
1. Go to Render Dashboard
2. Click "New" → "Blueprint"
3. Connect your GitHub repository: `nnaraya180/PersonalOrganization`
4. Render will automatically detect `render.yaml`
5. Click "Apply" to create both services

### Option B: Manual Setup
If Blueprint doesn't work, create services manually:

#### Backend Service:
1. New → Web Service
2. Connect repository
3. Settings:
   - **Name**: `meal-mood-backend`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r ../requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### Frontend Service:
1. New → Static Site
2. Connect repository
3. Settings:
   - **Name**: `meal-mood-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`

## Step 3: Configure Environment Variables

### Backend Service:
1. Go to your backend service dashboard
2. Navigate to "Environment" tab
3. Add the following:
   - **Key**: `LITELLM_TOKEN`
   - **Value**: (paste your Duke LiteLLM token)
   
⚠️ **IMPORTANT**: Without this token, the chat functionality won't work!

### Frontend Service:
No additional environment variables needed - `.env.production` is used during build.

## Step 4: Update URLs

After deployment, you'll get URLs like:
- Backend: `https://meal-mood-backend.onrender.com`
- Frontend: `https://meal-mood-frontend.onrender.com`

**Update these files with your actual URLs:**

1. **Backend CORS** (`backend/main.py`):
   ```python
   allowed_origins = [
       "http://localhost:5173",
       "http://localhost:3000",
       "https://meal-mood-frontend.onrender.com",  # ← Update this
   ]
   ```

2. **Frontend Environment** (`frontend/.env.production`):
   ```
   VITE_API_URL=https://meal-mood-backend.onrender.com  # ← Update this
   ```

3. Commit and push changes - Render will auto-redeploy

## Step 5: Wait for Deployment

- Backend typically takes 2-5 minutes
- Frontend typically takes 1-3 minutes
- Watch the logs in Render dashboard for any errors

## Step 6: Test Your App

1. Visit your frontend URL: `https://meal-mood-frontend.onrender.com`
2. Test the Dashboard tab (should load fake data)
3. Test the Pantry tab (should connect to backend API)
4. Test the Chat tab (requires LITELLM_TOKEN to be set)

## Troubleshooting

### Backend won't start:
- Check logs for missing dependencies
- Verify `LITELLM_TOKEN` is set
- Check that `requirements.txt` is at root level

### Frontend is blank:
- Check browser console for errors
- Verify `VITE_API_URL` is correct
- Check that CORS origins in backend match frontend URL

### API calls failing:
- Verify backend URL in `.env.production` matches actual backend URL
- Check CORS settings in `backend/main.py`
- Look at backend logs for errors

### Database issues:
- Render free tier uses ephemeral storage
- Database will reset on each deploy
- Consider adding Render PostgreSQL for persistence (optional)

## Free Tier Limitations

⚠️ Render free tier:
- Backend spins down after 15 min of inactivity
- First request after spin-down takes 30-60 seconds
- 750 hours/month free
- Limited to 512MB RAM

## Upgrading to Paid (Optional)

For always-on service and better performance:
- Backend: $7/month (Starter plan)
- Persistent database: $7/month (if needed)
- Frontend: Free (static sites are always free)

## Local Development

To run locally after these changes:
```bash
# Backend
cd backend
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm run dev
```

The app will automatically use `.env.development` for local API calls.

## Git Workflow

```bash
# After making changes locally
git add .
git commit -m "Update deployment configuration"
git push origin main

# Render will automatically detect changes and redeploy
```

## Support

If you encounter issues:
1. Check Render logs (each service has a "Logs" tab)
2. Verify all environment variables are set
3. Ensure both services are deployed successfully
4. Check browser console for frontend errors

---

**Next Steps:**
1. Deploy to Render using Blueprint or manual setup
2. Copy your actual service URLs
3. Update `backend/main.py` and `frontend/.env.production` with real URLs
4. Commit and push to trigger redeployment
5. Share your public URL! 🎉
