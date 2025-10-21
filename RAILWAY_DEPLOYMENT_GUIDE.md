# Railway Deployment Guide - Redis Background Jobs

## Understanding the Architecture Change

### Before (Session-Based)
```
User's Browser → Streamlit (Railway) → Runs Analysis → Browser displays results
                    ↑
                    └─ Analysis runs HERE in Streamlit process
                    └─ If browser closes/locks, analysis STOPS
```

### After (Background Jobs)
```
User's Browser → Streamlit (Railway) → Submits Job to Redis Queue
                                              ↓
                                         RQ Worker (Railway) → Runs Analysis
                                              ↓
                                         Saves to Database
                                              ↓
                                         Browser polls for results
```

**Key Change**: Analysis now runs in a **separate worker process on Railway's servers**, completely independent of the user's browser session.

- **User's Browser**: Only displays UI and polls for updates (can close/lock safely)
- **Streamlit Process**: Just shows the UI and submits jobs (on Railway)
- **Worker Process**: NEW - Actually runs the analysis (on Railway, separate from browser)
- **Redis**: Job queue connecting Streamlit and Worker (on Railway)

## Step-by-Step Deployment

### Step 1: Add memo_content Column to Production Database

**Option A: Using Railway Dashboard (Recommended)**
1. Go to Railway dashboard
2. Click on your PostgreSQL database
3. Click "Data" tab
4. Click "Query" button
5. Paste this SQL:
   ```sql
   ALTER TABLE analyses ADD COLUMN IF NOT EXISTS memo_content TEXT;
   ```
6. Click "Run Query"

**Option B: Using Railway CLI**
```bash
railway run psql $DATABASE_URL -c "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS memo_content TEXT;"
```

**Verify it worked:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'analyses' AND column_name = 'memo_content';
```

You should see:
```
column_name   | data_type
--------------+-----------
memo_content  | text
```

### Step 2: Deploy Your Code to Railway

Your code changes are ready. Just deploy:

```bash
# Commit changes
git add .
git commit -m "Add Redis background job processing for ASC 606"

# Push to Railway (deploys automatically)
git push
```

**What Railway will deploy:**
- Web process: `gunicorn backend_api:app` (your Flask API)
- Worker process: `python worker.py` (NEW - but will fail until Redis is added)

The worker will show errors until you add Redis - **this is expected**.

### Step 3: Add Redis Service to Railway

1. Go to your Railway project dashboard
2. Click **"+ New"** button
3. Select **"Database"**
4. Click **"Add Redis"**
5. Railway will automatically:
   - Create a Redis instance
   - Set the `REDIS_URL` environment variable
   - Restart your services

**Cost**: ~$5-10/month for Redis

### Step 4: Verify Everything is Running

Wait 2-3 minutes for services to restart, then check logs:

**Check Worker is Running:**
```bash
railway logs --service worker
```

You should see:
```
🚀 RQ Worker started. Waiting for jobs...
```

**Check Web is Running:**
```bash
railway logs --service web
```

Should show Flask server running without errors.

**Check Redis is Accessible:**
```bash
railway run redis-cli ping
```

Should return: `PONG`

### Step 5: Test with a Real Analysis

1. Go to your production website
2. Navigate to ASC 606 page
3. Upload a **small test contract** (< 1000 words)
4. Click "Confirm & Analyze"
5. **Close the browser tab** immediately
6. Wait 2-3 minutes
7. Reopen the ASC 606 page
8. Verify analysis completed and memo is displayed

**What to check:**
- ✅ Analysis completes even though you closed the browser
- ✅ User was charged correct amount (check database)
- ✅ Memo is saved in database (memo_content column)
- ✅ No duplicate charges (check credit_transactions table)

### Step 6: Monitor for Issues

**Check for failed jobs:**
```bash
railway run redis-cli LLEN rq:queue:failed
```

If > 0, inspect failed jobs:
```bash
railway run redis-cli LRANGE rq:queue:failed 0 -1
```

**Check analysis records:**
```bash
railway run psql $DATABASE_URL -c "SELECT analysis_id, status, final_charged_credits, error_message FROM analyses ORDER BY started_at DESC LIMIT 10;"
```

**Verify no double charges:**
```bash
railway run psql $DATABASE_URL -c "SELECT memo_uuid, COUNT(*) FROM credit_transactions WHERE reason = 'analysis_charge' GROUP BY memo_uuid HAVING COUNT(*) > 1;"
```

Should return 0 rows.

## Deployment Order Summary

```
1. Add memo_content column to production DB ✅
   └─ Prevents "column does not exist" errors

2. Deploy code to Railway ✅
   └─ Worker will fail (expected) - needs Redis

3. Add Redis service ✅
   └─ Railway auto-sets REDIS_URL and restarts services

4. Verify all services running ✅
   └─ Check logs for worker, web, redis

5. Test with real analysis ✅
   └─ Close browser and verify it completes

6. Monitor for issues ✅
   └─ Check failed jobs, double charges
```

## Environment Variables to Verify

Make sure these are set in Railway:
- ✅ `DATABASE_URL` - PostgreSQL connection (set by Railway)
- ✅ `REDIS_URL` - Redis connection (set by Railway after Step 3)
- ✅ `WEBSITE_URL` - Your production URL (e.g., https://www.veritaslogic.ai)
- ✅ `OPENAI_API_KEY` - Your OpenAI key
- ✅ `STRIPE_SECRET_KEY` - Your Stripe key
- ✅ All other existing secrets

## Troubleshooting

### Worker Shows "Connection Refused"
**Cause**: Redis not added yet  
**Fix**: Complete Step 3 (add Redis service)

### "Column memo_content does not exist"
**Cause**: Step 1 not completed  
**Fix**: Run the ALTER TABLE command on production DB

### Worker Shows "Cannot assign requested address"
**Cause**: REDIS_URL not set correctly  
**Fix**: Check Railway dashboard that Redis service is running and REDIS_URL env var is set

### Analysis Never Completes
**Cause**: Worker not processing jobs  
**Fix**: Check worker logs, verify Redis connection, check queue length:
```bash
railway run redis-cli LLEN rq:queue:analysis
```

### User Charged Twice
**Cause**: Idempotency check not working  
**Fix**: This shouldn't happen with our implementation. Contact support if it does.

## Rollback Plan (If Needed)

If something goes wrong, you can temporarily disable background jobs:

1. In `asc606/asc606_page.py`, line 343-350:
   ```python
   # Comment out job submission
   # from asc606.job_analysis_runner import submit_and_monitor_asc606_job
   # submit_and_monitor_asc606_job(...)
   
   # Uncomment old synchronous analysis
   perform_asc606_analysis_new(pricing_result, additional_context, user_token, cached_combined_text=cached_text, uploaded_filenames=uploaded_filenames)
   ```

2. Deploy
3. Analyses will run synchronously again (user must keep browser open)

## Success Criteria

✅ Worker logs show "RQ Worker started"  
✅ Test analysis completes with browser closed  
✅ User charged correct amount (1 transaction only)  
✅ Memo saved to database  
✅ No errors in logs  
✅ Failed analyses show $0 charge

Once all green, you're production-ready! 🚀
