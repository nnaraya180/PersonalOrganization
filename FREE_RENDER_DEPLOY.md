# Free Render Deployment Guide

## Step 1: Deploy Backend (Free Web Service)

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository (`PersonalOrganization`)
4. Configure as follows:

### Backend Configuration:
- **Name**: `meal-mood-backend` (or any name you want)
- **Root Directory**: `backend`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r ../requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Instance Type**: **Free** ✅

5. Click **"Create Web Service"**
6. **Copy your backend URL** when it's deployed (looks like `https://meal-mood-backend.onrender.com`)

### Add Environment Variables:
After the service is created:
1. Go to your backend service dashboard
2. Navigate to **"Environment"** tab
3. Add: **Key**: `LITELLM_TOKEN` | **Value**: (your Duke LiteLLM token)
4. Click "Save"

---

## Step 2: Deploy Frontend (Free Static Site)

### A. Prepare Frontend Files

**Create `.env.production`** in frontend directory:
```
VITE_API_URL=https://meal-mood-backend.onrender.com
```
(Replace with your actual backend URL from Step 1)

### B. Deploy to Render

1. Click **"New +"** → **"Static Site"**
2. Connect your GitHub repository
3. Configure as follows:

### Frontend Configuration:
- **Name**: `meal-mood-frontend` (or any name you want)
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`

4. Click **"Create Static Site"**

---

## Step 3: Update Backend CORS (After Getting Frontend URL)

After your frontend is deployed:

1. **Copy your frontend URL** from Render dashboard (looks like `https://meal-mood-frontend.onrender.com`)
2. Go to your **backend service**
3. Navigate to **"Environment"** tab
4. Update the CORS configuration in your code:

**File**: `backend/main.py`

Update this section with your actual URLs:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://YOUR-BACKEND-URL.onrender.com",
        "https://YOUR-FRONTEND-URL.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

5. Commit and push changes:
```bash
git add backend/main.py
git commit -m "Update CORS for production URLs"
git push
```

6. Render will automatically redeploy your backend

---

## Free Tier Limitations (Important!)

⚠️ **You need to know about these**:

1. **Spins Down After Inactivity**: Backend goes to sleep after 15 minutes of no requests
2. **Cold Start**: First request after sleep takes 30-60 seconds
3. **Monthly Hours**: 750 free hours per month (enough for most use cases)
4. **Storage**: Database resets on each deploy (ephemeral)
5. **No Custom Domain**: Uses `onrender.com` subdomain

**To keep it awake** (optional):
- Add a simple monitoring service (like uptime robot)
- Or just expect the first request to be slow

---

## Test Your Deployment

1. Visit your frontend URL: `https://your-frontend-url.onrender.com`
2. Check browser console (F12) for errors
3. Test the Pantry tab (should connect to backend)
4. Test the Chat tab (requires LITELLM_TOKEN)

---

## Troubleshooting

### Backend won't start:
```
1. Check "Logs" tab in Render dashboard
2. Look for Python errors
3. Verify LITELLM_TOKEN is set
4. Check requirements.txt has all dependencies
```

### Frontend is blank:
```
1. Open browser console (F12)
2. Look for CORS errors
3. Check that API_URL is correct in .env.production
4. Make sure backend URL is accessible
```

### API calls failing:
```
1. Verify both services are "Live" in Render
2. Check CORS origins match your actual URLs
3. Wait 60+ seconds for cold start
4. Check both services' logs
```

---

## Next Steps

1. ✅ Deploy backend (get URL)
2. ✅ Deploy frontend (get URL)
3. ✅ Update `.env.production` with backend URL
4. ✅ Update `backend/main.py` CORS with both URLs
5. ✅ Push changes (auto-redeploy)
6. ✅ Test your app!

---

## Upgrading Later (Optional)

If you want to avoid cold starts and keep it always-on:
- **Paid Plans**: Start at $7/month per service
- But free tier works great for learning and testing!

Good luck! 🚀
