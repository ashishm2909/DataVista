# Deploy to Render.com - Step by Step

## Prerequisites
- GitHub account with your project pushed
- Render.com account

## Step 1: Push to GitHub
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

## Step 2: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub
3. Click "New" → "Web Service"

## Step 3: Deploy Web Service
1. Connect your GitHub repository
2. Configure:
   - Name: `dashboard`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn dashboard_platform.wsgi --bind 0.0.0.0:$PORT`
3. Click "Create Web Service"

## Step 4: Add PostgreSQL Database
1. In Render dashboard, click "New" → "PostgreSQL"
2. Configure:
   - Name: `dashboard-db`
   - Plan: `Free`
3. Click "Create Database"
4. Copy the `Internal Database URL` (starts with `postgres://`)

## Step 5: Connect Database
1. Go to your web service dashboard
2. Click "Environment" → "Add Environment Variable"
3. Add: `DATABASE_URL` = (paste the PostgreSQL URL from step 4)
4. Add: `ALLOWED_HOSTS` = `your-service-name.onrender.com`
5. Add: `CSRF_TRUSTED_ORIGINS` = `https://your-service-name.onrender.com`
6. Add: `SECRET_KEY` = (generate a random string)

## Step 6: Deploy
1. Trigger a new deploy (or push a commit)
2. Watch logs for any errors
3. Once deployed, visit `https://your-service-name.onrender.com`

## Troubleshooting

### 500 Error on First Visit
- Check logs in Render dashboard
- Ensure DATABASE_URL is set
- Verify migrations ran (check release logs)

### Static Files Not Loading
- Ensure `whitenoise` is in requirements.txt
- STATIC_ROOT should be set to `staticfiles`

### Uploaded Files Lost on Restart
- This is expected on Render's free tier (ephemeral filesystem)
- For production, add a persistent disk or use cloud storage (AWS S3)

## Important Notes
- Render's free tier sleeps after 15 min of inactivity (cold starts)
- Free PostgreSQL expires after 90 days (set reminder)
- Files uploaded will be lost on each deployment/restart