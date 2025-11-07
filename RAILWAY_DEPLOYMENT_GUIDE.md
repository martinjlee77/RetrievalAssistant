# Railway Production Deployment Guide
## Subscription System Migration

---

## ⚠️ CRITICAL: Read This First

This deployment migrates from credit-based to subscription-based billing. The migration is **irreversible** without a database backup. Follow these steps exactly.

**Estimated Time:** 30-45 minutes  
**Downtime:** 5-10 minutes (during migration)

---

## PRE-DEPLOYMENT CHECKLIST

### ✅ Backups
- [ ] Database backup completed
- [ ] Current git commit noted for rollback
- [ ] Current Railway deployment screenshot saved

### ✅ Prerequisites
- [ ] PostgreSQL client (`psql`) installed locally
- [ ] Railway `DATABASE_PUBLIC_URL` copied from project dashboard
- [ ] Git repository clean (no uncommitted changes)
- [ ] All team members notified of maintenance window

---

## DEPLOYMENT SEQUENCE

### PHASE 1: DATABASE MIGRATION (15 minutes)

#### Step 1: Connect to Railway PostgreSQL

```bash
psql "postgresql://postgres:YOUR_PASSWORD@ballast.proxy.rlwy.net:15493/railway"
```

**How to get the connection string:**
1. Go to Railway project dashboard
2. Click on PostgreSQL service
3. Go to "Variables" tab
4. Copy `DATABASE_PUBLIC_URL` value
5. Replace the placeholder above with your actual connection string
6. **Important:** Keep the double quotes around the entire URL

#### Step 2: Verify Current Schema

Before running migration, verify you're connected to the right database:

```sql
-- Check current tables
\dt

-- Should see: analyses, credit_transactions, email_verification_tokens, 
-- password_reset_tokens, users

-- Count existing users
SELECT COUNT(*) FROM users;

-- Exit psql
\q
```

#### Step 3: Run Migration Script

**IMPORTANT:** Copy the entire contents of `database/railway_migration.sql` and paste into psql session.

```bash
# Connect again
psql "postgresql://postgres:YOUR_PASSWORD@ballast.proxy.rlwy.net:15493/railway"

# Then paste the ENTIRE contents of database/railway_migration.sql
# (Copy from line 1 to the very last line)
```

**Expected Output:**
```
CREATE TABLE
CREATE TABLE
...
NOTICE: ==============================================
NOTICE: VeritasLogic Subscription Migration Complete!
NOTICE: ==============================================
```

#### Step 4: Verify Migration Success

```sql
-- Check new tables were created
\dt

-- Should now see: organizations, subscription_plans, subscription_instances, 
-- subscription_usage, rollover_ledger, stripe_webhook_events, lead_sources

-- Verify subscription plans were seeded
SELECT id, plan_key, name, price_monthly, word_allowance FROM subscription_plans;

-- Expected output:
--  id | plan_key     | name         | price_monthly | word_allowance
-- ----+--------------+--------------+---------------+----------------
--   1 | professional | Professional |        295.00 |          30000
--   2 | team         | Team         |        595.00 |          75000
--   3 | enterprise   | Enterprise   |       1195.00 |         180000

-- Exit psql
\q
```

**✅ Checkpoint:** If you don't see all 3 plans, DO NOT PROCEED. Check migration logs for errors.

---

### PHASE 2: UPDATE STRIPE PRICE IDs (5 minutes)

You need to update the placeholder Stripe price IDs with your actual Stripe prices.

#### Step 1: Get Stripe Price IDs

1. Log into Stripe Dashboard → Products
2. Find your three subscription products
3. Copy the `price_xxxxx` IDs for each tier

#### Step 2: Update Database

```bash
# Connect to Railway database
psql "postgresql://postgres:YOUR_PASSWORD@ballast.proxy.rlwy.net:15493/railway"
```

```sql
-- Update with your actual Stripe price IDs
UPDATE subscription_plans SET stripe_price_id = 'price_ACTUAL_PROFESSIONAL_ID' WHERE plan_key = 'professional';
UPDATE subscription_plans SET stripe_price_id = 'price_ACTUAL_TEAM_ID' WHERE plan_key = 'team';
UPDATE subscription_plans SET stripe_price_id = 'price_ACTUAL_ENTERPRISE_ID' WHERE plan_key = 'enterprise';

-- Verify
SELECT plan_key, stripe_price_id FROM subscription_plans;

\q
```

---

### PHASE 3: ENVIRONMENT VARIABLES (10 minutes)

#### Required Variables Checklist

Go to Railway Project → Settings → Variables and verify these exist:

**Database (Auto-configured by Railway):**
- ✅ `DATABASE_URL` (should already exist)

**Redis (CRITICAL for worker queue):**
- ⚠️ `REDIS_URL` - Must be configured! Check Redis addon is attached.

**API Keys:**
- ⚠️ `OPENAI_API_KEY` - Required for analysis
- ⚠️ `POSTMARK_API_KEY` - Required for emails (signup verification, password resets)

**Stripe:**
- ⚠️ `STRIPE_SECRET_KEY` - Payment processing
- ⚠️ `STRIPE_PUBLISHABLE_KEY` - Frontend Stripe integration  
- ⚠️ `STRIPE_WEBHOOK_SECRET` - Webhook signature verification

**Security:**
- ⚠️ `SECRET_KEY` - JWT token signing (use long random string)

**URLs (Optional - auto-detected):**
- `WEBSITE_URL` (defaults to production URL)
- `STREAMLIT_URL` (defaults to production URL)

**Bot Protection (Optional but recommended):**
- `RECAPTCHA_SECRET_KEY`
- `RECAPTCHA_SITE_KEY`

#### Generate Strong SECRET_KEY

```bash
# Run this locally to generate a secure key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the output and set it as `SECRET_KEY` in Railway.

---

### PHASE 4: CODE DEPLOYMENT (10 minutes)

#### Step 1: Push to Git

```bash
# Verify you're on the right branch
git branch

# Stage all changes
git add .

# Commit with descriptive message
git commit -m "feat: Migrate to subscription-based billing system

- Add subscription tables (plans, instances, usage, rollover_ledger)
- Update users and analyses tables for org support
- Implement word allowance tracking
- Add trial subscription flow with credit card
- Stripe integration for recurring billing
- Past-due blocking enforcement"

# Push to your main branch (this triggers Railway deployment)
git push origin main
```

#### Step 2: Monitor Railway Deployment

1. Go to Railway project dashboard
2. Click on your service
3. Watch the "Deployments" tab
4. Wait for status: **"Success"** (usually 3-5 minutes)

**⚠️ If deployment fails:**
- Check build logs in Railway
- Common issues: Missing environment variables, Python dependency errors
- Fix and push again

---

### PHASE 5: VERIFICATION (10 minutes)

#### Test 1: Backend Health Check

```bash
# Test if backend is responding
curl https://www.veritaslogic.ai/api/subscription/plans

# Expected: JSON array with 3 subscription plans
```

#### Test 2: Signup Flow (CRITICAL)

1. Open incognito browser → `https://www.veritaslogic.ai/signup`
2. Fill out signup form with test email
3. Enter test credit card (Stripe test mode):
   - Card: `4242 4242 4242 4242`
   - Expiry: Any future date
   - CVC: Any 3 digits
4. Submit signup
5. **Verify:**
   - Account created successfully
   - Email verification sent
   - Trial subscription created

#### Test 3: Verify Trial in Database

```bash
psql "postgresql://postgres:YOUR_PASSWORD@ballast.proxy.rlwy.net:15493/railway"
```

```sql
-- Check latest subscription instance
SELECT 
    o.name as org_name, 
    u.email,
    si.status, 
    si.trial_end_date,
    sp.name as plan_name,
    su.word_allowance,
    su.words_used
FROM subscription_instances si
JOIN organizations o ON si.org_id = o.id
JOIN subscription_plans sp ON si.plan_id = sp.id
JOIN users u ON u.org_id = o.id
LEFT JOIN subscription_usage su ON su.subscription_id = si.id
ORDER BY si.created_at DESC
LIMIT 1;

-- Expected:
-- status = 'trial'
-- word_allowance = 9000
-- words_used = 0

\q
```

#### Test 4: Analysis Flow (Critical Path)

1. Log into test account
2. Navigate to ASC 606 analysis page
3. Upload a sample contract
4. **Verify pricing display shows:**
   - Total words in contract
   - Words remaining in allowance
   - "9,000 words available" for trial
5. Click "Confirm & Analyze"
6. **Wait for analysis to complete** (3-20 minutes)
7. **Verify:**
   - Memo generated successfully
   - Words deducted from allowance

#### Test 5: Word Deduction Verification

```bash
psql "postgresql://postgres:YOUR_PASSWORD@ballast.proxy.rlwy.net:15493/railway"
```

```sql
-- Check that words were deducted
SELECT 
    o.name,
    su.words_used,
    su.word_allowance,
    (su.word_allowance - su.words_used) as remaining
FROM subscription_usage su
JOIN organizations o ON su.org_id = o.id
ORDER BY su.updated_at DESC
LIMIT 1;

-- words_used should be > 0 after analysis

\q
```

---

## POST-DEPLOYMENT MONITORING

### First 24 Hours

Monitor these metrics:

1. **Signup Success Rate**
   ```sql
   -- Count signups in last 24 hours
   SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours';
   ```

2. **Trial Activations**
   ```sql
   -- Count trials created
   SELECT COUNT(*) FROM subscription_instances 
   WHERE status = 'trial' AND created_at > NOW() - INTERVAL '24 hours';
   ```

3. **Analysis Completion Rate**
   ```sql
   -- Check for failed analyses
   SELECT COUNT(*) FROM analyses 
   WHERE status = 'failed' AND created_at > NOW() - INTERVAL '24 hours';
   ```

4. **Stripe Webhook Delivery**
   - Check Stripe Dashboard → Developers → Webhooks
   - Verify events are being received successfully

---

## TROUBLESHOOTING

### Issue: "Invalid token" errors after deployment

**Cause:** JWT tokens signed with old SECRET_KEY are invalid  
**Fix:** Users need to log out and log in again

### Issue: Analysis stuck in queue

**Cause:** REDIS_URL not configured  
**Fix:** 
1. Verify Redis addon is attached in Railway
2. Check `REDIS_URL` environment variable exists
3. Restart worker service

### Issue: Email verification not sending

**Cause:** POSTMARK_API_KEY missing or invalid  
**Fix:** Verify Postmark API key in Railway environment variables

### Issue: Stripe payment fails during signup

**Cause:** STRIPE_SECRET_KEY or STRIPE_PUBLISHABLE_KEY incorrect  
**Fix:** Verify Stripe keys match your account (test vs production)

### Issue: "Table does not exist" errors

**Cause:** Migration script not run or failed  
**Fix:** Re-run migration script and check for errors

---

## ROLLBACK PROCEDURE (Emergency Only)

If critical issues arise:

### Step 1: Revert Code
```bash
# Get commit hash from before migration
git log --oneline

# Revert to previous commit
git revert <commit-hash>
git push origin main
```

### Step 2: Restore Database Backup
- Use your Railway database backup
- This is why the pre-deployment backup is CRITICAL
- Contact Railway support if needed

---

## SUCCESS CRITERIA

✅ Migration is successful when:
- [ ] New users can signup with credit card
- [ ] Trial subscriptions created automatically (9,000 words)
- [ ] Allowance check displays correctly before analysis
- [ ] Analysis completes and deducts words from allowance
- [ ] No 500 errors in production logs
- [ ] Stripe webhooks receiving events successfully

---

**Last Updated:** November 2025  
**Migration Version:** 1.0
