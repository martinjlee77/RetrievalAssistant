# VeritasLogic Railway Deployment Guide

## What's Ready
Your code is now configured for Railway deployment with:
- Flask website (authentication, marketing)  
- Streamlit analysis platform (ASC standards)
- PostgreSQL database configuration
- Environment variables setup
- Auto-scaling configuration

## Railway Deployment Steps

### 1. Push to GitHub
Your Replit automatically syncs to GitHub - no action needed!

### 2. Railway Setup
1. Go to railway.app and sign up with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository

### 3. Deploy Services
**Website Service (Flask):**
- Root directory: `.`
- Build command: `pip install -r website-requirements.txt`
- Start command: `python start_website.py`

**Analysis Service (Streamlit):**
- Root directory: `.`  
- Build command: `pip install -r analysis-requirements.txt`
- Start command: `python start_analysis.py`

### 4. Environment Variables
Set these in Railway for both services:
- `DATABASE_URL` (from your existing PostgreSQL)
- `SECRET_KEY` (generate new one)
- `JWT_SECRET` (generate new one)

### 5. Custom Domains
- Website: `veritaslogic.ai`
- Analysis: `app.veritaslogic.ai`

## Testing Your Deployment
1. Visit your website URL - should show marketing page
2. Register/login - should work with database
3. Click "Launch Analysis" - should redirect to Streamlit
4. Test ASC analysis features

## Development Workflow
After deployment:
1. Make changes in Replit
2. Changes auto-sync to GitHub
3. Railway auto-deploys in 2-3 minutes
4. Test on live site

Ready to deploy!