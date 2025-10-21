# Redis Background Job Implementation for ASC 606

## Overview
Implemented Redis + RQ background job processing system to solve the critical production issue where analyses stop when users close their browser, lock their screen, or switch tabs.

## Implementation Complete

### 1. Core Infrastructure ✅
- **shared/job_manager.py**: Job submission, status checking, and progress tracking
- **workers/analysis_worker.py**: Background worker that runs ASC 606 analysis
- **worker.py**: RQ worker startup script
- **workers/__init__.py**: Package initialization

### 2. Database Changes ✅
- Added `memo_content` TEXT column to `analyses` table (stores complete memo)
- Added `error_message` TEXT column to `analyses` table (already existed in production)

### 3. Backend API ✅
- New endpoint: `POST /api/analysis/save`
  - Called by worker to save completed analysis with memo content
  - Handles billing (only charges on success)
  - Stores memo content in database
  - Creates credit transactions

### 4. Frontend Changes ✅
- **asc606/asc606_page.py**: Modified to use job submission instead of synchronous analysis
- **asc606/job_analysis_runner.py**: New module for job submission and progress polling
  - Submits job to Redis queue
  - Polls every 10 seconds for status
  - Displays real-time progress (Step 1/5, Step 2/5, etc.)
  - Shows completion and saves to session state

### 5. Deployment Configuration ✅
- **Procfile**: Configured for Railway with web and worker processes
  ```
  web: gunicorn backend_api:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  worker: python worker.py
  ```

## Railway Deployment Steps

### 1. Add Redis Service
1. In Railway project, click "+ New"
2. Select "Database" → "Add Redis"
3. Railway will automatically set `REDIS_URL` environment variable

### 2. Add Worker Process
1. In Railway project settings, go to "Settings" → "Deployments"
2. Add new service with start command: `python worker.py`
3. Or Railway will auto-detect from Procfile

### 3. Environment Variables
Ensure these are set:
- `REDIS_URL`: Automatically set by Railway Redis service
- `DATABASE_URL`: PostgreSQL connection string
- `WEBSITE_URL`: Your production URL (e.g., https://www.veritaslogic.ai)
- All existing secrets (OpenAI, Stripe, etc.)

## How It Works (BILLING-SAFE ARCHITECTURE)

### User Flow (New)
1. User uploads contract and clicks "Confirm & Analyze"
2. **Backend creates analysis record** with server-validated pricing (status='processing')
3. **Job submitted to Redis queue** (returns immediately)
4. User sees progress updates every 10 seconds
5. User can close tab, lock screen, switch tabs - **analysis continues**
6. When complete, worker updates existing record with memo
7. User sees completion message and results

### Worker Flow (Billing-Safe)
1. Worker picks up job from Redis queue
2. Runs all 5 ASC 606 analysis steps (raises exception on ANY step failure)
3. Updates job progress after each step
4. Generates final memo
5. **Calls `/api/analysis/save` with minimal data** (memo_content, success, error only)
6. **Backend retrieves authoritative pricing from database** (created in step 2 above)
7. Backend updates analysis record and charges user atomically
8. Worker marks job as complete with result

### Billing Safety (HARDENED)
- **Two-phase commit**: Analysis record created FIRST with authoritative pricing, then job submitted
- **Server-side pricing**: Backend recalculates ALL costs from database record (never trusts worker)
- **Idempotency**: Database status check prevents duplicate charges even on worker retry
- **Atomic save+charge**: Single transaction updates memo and deducts credits
- **Failure protection**: Worker raises exception on any step failure (prevents billing for degraded output)
- **Authorization**: Backend verifies user owns analysis before allowing save
- User is **only charged when worker successfully completes ALL steps**
- Failed analyses: $0 charge, error saved to database

## Testing Checklist (On Railway)

### Pre-Deployment
- [ ] Redis service added to Railway
- [ ] Worker process configured
- [ ] All environment variables set

### Post-Deployment
- [ ] Check worker logs: Should show "🚀 RQ Worker started. Waiting for jobs..."
- [ ] Submit test analysis with small contract
- [ ] Verify job appears in queue: `redis-cli LLEN rq:queue:analysis`
- [ ] Watch worker logs for progress
- [ ] Close browser tab mid-analysis
- [ ] Reopen and verify analysis completed
- [ ] Check database for saved memo_content
- [ ] Verify user was charged correct amount
- [ ] Test failure scenario (invalid contract)
- [ ] Verify no charge on failure

### Monitoring Commands (Railway CLI)
```bash
# Check worker status
railway logs --service worker

# Check Redis queue length
railway run redis-cli LLEN rq:queue:analysis

# Check failed jobs
railway run redis-cli LLEN rq:queue:failed

# View job details
railway run redis-cli HGETALL rq:job:<job_id>
```

## Key Features

### Billing Safety Architecture
**Two-Phase Commit Pattern:**
1. **Phase 1 (Frontend)**: Create analysis record with server-validated pricing
   - `/api/analysis/create` endpoint validates pricing server-side
   - Stores authoritative cost in database with status='processing'
   - Prevents worker tampering by establishing pricing BEFORE job runs
   
2. **Phase 2 (Worker)**: Update record with results
   - Worker sends minimal payload (memo_content, success flag only)
   - Backend retrieves pricing from database (Phase 1 record)
   - Update and charge happen in single atomic transaction
   - Idempotency check prevents duplicate charges on retry

**Why This is Safe:**
- ✅ Worker cannot manipulate pricing (backend ignores worker cost fields)
- ✅ No double-charging (idempotency via database status check)
- ✅ No charging for failures (worker raises on step failure, backend checks success flag)
- ✅ User authorization (backend verifies user_id owns analysis_id)
- ✅ Atomic operations (update + charge in single transaction)

### Progress Tracking
Worker updates job metadata after each step:
```python
job.meta['progress'] = {
    'current_step': 3,
    'total_steps': 5,
    'step_name': 'Step 3',
    'updated_at': datetime.now().isoformat()
}
```

### User Experience
- ✅ Can close browser safely
- ✅ Can lock screen
- ✅ Can switch tabs
- ✅ Real-time progress updates
- ✅ Results saved automatically
- ✅ No more "DO NOT CLOSE THIS TAB!" warnings

### Billing Safety
- ✅ Only charges on successful completion
- ✅ Failed analyses: $0 charge
- ✅ Atomic save + billing in single transaction
- ✅ Full audit trail in database

## Cost Estimate (Railway)
- **Redis**: ~$5-10/month (512MB plan)
- **Worker Dyno**: Included in Railway plan (shares resources)
- **Total Additional Cost**: ~$5-10/month

## Next Steps for Other Standards
Once ASC 606 is tested and working on Railway:
1. Copy `asc606/job_analysis_runner.py` → `asc718/job_analysis_runner.py`
2. Update imports and function names for ASC 718
3. Modify `workers/analysis_worker.py` to handle multiple standards
4. Repeat for ASC 805, 842, 340-40

## Rollback Plan
If issues occur:
1. In ASC 606 page, comment out job submission code
2. Uncomment old `perform_asc606_analysis_new()` call
3. Redeploy (synchronous mode restored)
4. No database changes needed (memo_content column is additive)

## Files Modified
- shared/job_manager.py (new)
- workers/analysis_worker.py (new)
- workers/__init__.py (new)
- worker.py (new)
- asc606/job_analysis_runner.py (new)
- asc606/asc606_page.py (modified - job submission)
- backend_api.py (modified - new /api/analysis/save endpoint)
- Procfile (modified - added worker process)
- Database: analyses table (added memo_content column)
