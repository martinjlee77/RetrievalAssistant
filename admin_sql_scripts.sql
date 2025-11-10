-- ============================================
-- VeritasLogic.ai - Admin SQL Scripts
-- Manual Billing Operations
-- ============================================

-- IMPORTANT: These scripts are for manual subscription management
-- Run them from Replit Database tool or psql command line


-- ============================================
-- QUICK CHECKS (Read-only)
-- ============================================

-- 1. VIEW ALL ACTIVE SUBSCRIPTIONS
-- Shows current status of all customers
SELECT 
    u.email,
    sp.plan_key,
    si.status,
    su.word_allowance,
    su.words_used,
    (su.word_allowance - su.words_used) as remaining,
    ROUND((su.words_used::numeric / su.word_allowance * 100), 1) as pct_used,
    su.month_start,
    su.month_end,
    si.stripe_subscription_id
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE si.status IN ('active', 'trialing')
ORDER BY u.email;


-- 2. FIND SPECIFIC CUSTOMER
-- Replace 'customer@example.com' with actual email
SELECT 
    u.id as user_id,
    u.email,
    u.org_id,
    si.id as subscription_id,
    si.stripe_subscription_id,
    si.status,
    sp.plan_key,
    su.word_allowance,
    su.words_used,
    (su.word_allowance - su.words_used) as remaining
FROM users u
LEFT JOIN subscription_instances si ON si.org_id = u.org_id
LEFT JOIN subscription_usage su ON su.subscription_id = si.id
LEFT JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE u.email = 'customer@example.com'
ORDER BY si.created_at DESC;


-- 3. UPCOMING RENEWALS (Next 7 days)
SELECT 
    u.email,
    sp.plan_key,
    su.month_end as renewal_date,
    su.words_used,
    su.word_allowance,
    (su.word_allowance - su.words_used) as remaining
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE si.status = 'active'
  AND su.month_end BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY su.month_end;


-- 4. CUSTOMERS NEAR WORD LIMIT (>90% used)
SELECT 
    u.email,
    sp.plan_key,
    su.word_allowance,
    su.words_used,
    (su.word_allowance - su.words_used) as remaining,
    ROUND((su.words_used::numeric / su.word_allowance * 100), 1) as pct_used
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE si.status = 'active'
  AND (su.words_used::numeric / su.word_allowance) > 0.9
ORDER BY pct_used DESC;


-- 5. ALL TRIALS (Pending conversion)
SELECT 
    u.email,
    u.created_at as signup_date,
    si.current_period_end as trial_ends,
    su.words_used as trial_words_used,
    si.stripe_subscription_id
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
WHERE si.status = 'trialing'
ORDER BY si.current_period_end;


-- ============================================
-- OPERATION 1: CONVERT TRIAL → PROFESSIONAL
-- ============================================

-- Step 1: Find the trial subscription
-- Replace 'customer@example.com' with actual email
SELECT 
    si.id as subscription_id,
    su.id as usage_id,
    u.email,
    si.status,
    su.word_allowance,
    su.words_used
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
WHERE u.email = 'customer@example.com' 
  AND si.status = 'trialing';

-- Step 2: Update subscription status to active
-- Replace {subscription_id} with value from Step 1
UPDATE subscription_instances
SET status = 'active', updated_at = NOW()
WHERE id = {subscription_id};

-- Step 3: Get Stripe billing period for Professional plan
SELECT 
    current_period_start::date as billing_start,
    current_period_end::date as billing_end
FROM subscription_instances
WHERE id = {subscription_id};

-- Step 4: Update word allowance to Professional (30K) with Stripe billing period
-- Replace {usage_id}, {billing_start}, {billing_end} with values from above
UPDATE subscription_usage
SET word_allowance = 30000,
    words_used = 0,  -- Reset usage (ignore trial words)
    month_start = '{billing_start}',  -- e.g., '2025-11-10'
    month_end = '{billing_end}',      -- e.g., '2025-12-09'
    updated_at = NOW()
WHERE id = {usage_id};

-- Step 4: Verify conversion worked
-- Replace 'customer@example.com' with actual email
SELECT 
    u.email,
    si.status,
    sp.plan_key,
    su.word_allowance,
    su.words_used
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE u.email = 'customer@example.com';
-- Should show: status='active', word_allowance=30000, words_used=0


-- ============================================
-- OPERATION 2: MONTHLY RENEWAL (Reset Words)
-- ============================================

-- Step 1: Find active subscription needing renewal
-- Replace 'customer@example.com' with actual email
SELECT 
    si.id as subscription_id,
    su.id as usage_id,
    u.email,
    sp.plan_key,
    su.word_allowance,
    su.words_used,
    su.month_end as last_period_end
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE u.email = 'customer@example.com' 
  AND si.status = 'active';

-- Step 2: Get NEW Stripe billing period (from subscription_instances)
-- This ensures alignment with Stripe's actual billing cycle
SELECT 
    current_period_start::date as new_month_start,
    current_period_end::date as new_month_end
FROM subscription_instances
WHERE id = {subscription_id};  -- Use subscription_id from Step 1

-- Step 3: Reset word usage with Stripe billing period
-- Replace {usage_id}, {new_month_start}, {new_month_end} with values from above
UPDATE subscription_usage
SET words_used = 0,
    month_start = '{new_month_start}',  -- e.g., '2025-11-10'
    month_end = '{new_month_end}',      -- e.g., '2025-12-09'
    updated_at = NOW()
WHERE id = {usage_id};

-- Step 4: Verify renewal aligned with Stripe
-- Replace 'customer@example.com' with actual email
SELECT 
    u.email,
    su.word_allowance,
    su.words_used,
    su.month_start,
    su.month_end,
    si.current_period_start::date as stripe_billing_start
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
WHERE u.email = 'customer@example.com';
-- Should show: words_used=0, month_start matches stripe_billing_start (NOT calendar month)


-- ============================================
-- OPERATION 3: MARK PAYMENT FAILED (Past Due)
-- ============================================

-- Find subscription by Stripe ID (from Stripe email)
-- Replace 'sub_xxxxx' with Stripe subscription ID
SELECT 
    si.id,
    u.email,
    si.status,
    si.stripe_subscription_id
FROM subscription_instances si
JOIN users u ON u.org_id = si.org_id
WHERE si.stripe_subscription_id = 'sub_xxxxx';

-- Mark as past_due
-- Replace 'sub_xxxxx' with Stripe subscription ID
UPDATE subscription_instances
SET status = 'past_due', updated_at = NOW()
WHERE stripe_subscription_id = 'sub_xxxxx';


-- ============================================
-- OPERATION 4: REACTIVATE AFTER PAYMENT SUCCESS
-- ============================================

-- Mark subscription active again after payment succeeds
-- Replace 'sub_xxxxx' with Stripe subscription ID
UPDATE subscription_instances
SET status = 'active', updated_at = NOW()
WHERE stripe_subscription_id = 'sub_xxxxx';


-- ============================================
-- OPERATION 5: CANCEL SUBSCRIPTION
-- ============================================

-- Find subscription to cancel
-- Replace 'customer@example.com' with actual email
SELECT 
    si.id,
    si.stripe_subscription_id,
    u.email,
    si.status
FROM subscription_instances si
JOIN users u ON u.org_id = si.org_id
WHERE u.email = 'customer@example.com'
  AND si.status IN ('active', 'trialing');

-- Cancel subscription
-- Replace 'sub_xxxxx' with Stripe subscription ID
UPDATE subscription_instances
SET status = 'cancelled', updated_at = NOW()
WHERE stripe_subscription_id = 'sub_xxxxx';


-- ============================================
-- OPERATION 6: MANUALLY ADJUST WORD ALLOWANCE
-- (For special cases, customer support, etc.)
-- ============================================

-- Step 1: Find current usage
-- Replace 'customer@example.com' with actual email
SELECT 
    su.id as usage_id,
    u.email,
    su.word_allowance,
    su.words_used,
    (su.word_allowance - su.words_used) as remaining
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
WHERE u.email = 'customer@example.com'
  AND si.status = 'active';

-- Step 2: Add bonus words (e.g., +10,000 for customer support issue)
-- Replace {usage_id} and {new_allowance} with appropriate values
UPDATE subscription_usage
SET word_allowance = {new_allowance},  -- e.g., 40000 (30K + 10K bonus)
    updated_at = NOW()
WHERE id = {usage_id};

-- Step 3: Verify adjustment
-- Replace 'customer@example.com' with actual email
SELECT 
    u.email,
    su.word_allowance,
    su.words_used,
    (su.word_allowance - su.words_used) as remaining
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
WHERE u.email = 'customer@example.com';


-- ============================================
-- DIAGNOSTIC QUERIES
-- ============================================

-- Check for orphaned usage records (no active subscription)
SELECT 
    su.id,
    su.org_id,
    su.word_allowance,
    su.words_used,
    su.created_at
FROM subscription_usage su
LEFT JOIN subscription_instances si ON su.subscription_id = si.id
WHERE si.id IS NULL OR si.status = 'cancelled';


-- Check for subscriptions without usage records (data integrity issue)
SELECT 
    si.id,
    u.email,
    si.status,
    si.stripe_subscription_id
FROM subscription_instances si
JOIN users u ON u.org_id = si.org_id
LEFT JOIN subscription_usage su ON su.subscription_id = si.id
WHERE si.status IN ('active', 'trialing')
  AND su.id IS NULL;


-- Get subscription history for customer (all past subscriptions)
-- Replace 'customer@example.com' with actual email
SELECT 
    si.id,
    sp.plan_key,
    si.status,
    si.created_at,
    si.updated_at,
    si.stripe_subscription_id
FROM subscription_instances si
JOIN users u ON u.org_id = si.org_id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE u.email = 'customer@example.com'
ORDER BY si.created_at DESC;


-- ============================================
-- BULK OPERATIONS (Use with caution!)
-- ============================================

-- Reset ALL active subscriptions after renewals
-- WARNING: This should rarely be needed. Always use per-customer scripts instead.
-- Only use if you need to sync everyone after Stripe billing cycle changes.
-- Uncomment to use:
/*
-- Step 1: First manually verify Stripe billing periods for all subscriptions
SELECT 
    si.id,
    si.stripe_subscription_id,
    si.current_period_start::date as stripe_start,
    si.current_period_end::date as stripe_end,
    su.month_start,
    su.month_end,
    CASE 
        WHEN su.month_start = si.current_period_start::date THEN 'aligned'
        ELSE 'MISALIGNED'
    END as status
FROM subscription_instances si
JOIN subscription_usage su ON su.subscription_id = si.id
WHERE si.status = 'active';

-- Step 2: Only if needed, reset each subscription to match Stripe periods
UPDATE subscription_usage su
SET words_used = 0,
    month_start = si.current_period_start::date,
    month_end = si.current_period_end::date,
    updated_at = NOW()
FROM subscription_instances si
WHERE su.subscription_id = si.id
  AND si.status = 'active';
*/


-- ============================================
-- EMERGENCY: Sync Database with Stripe
-- ============================================

-- Step 1: Export all active subscriptions from Stripe Dashboard (CSV)
-- Step 2: For each subscription, get Stripe billing period from Stripe Dashboard:
--         Customers → Click customer → View subscription → Copy dates

-- Step 3: For each subscription in Stripe but not in database, insert manually:
-- CRITICAL: Use STRIPE billing dates, NOT calendar months!
-- Get these from Stripe Dashboard for each subscription:
--   current_period_start (e.g., 2025-11-10)
--   current_period_end (e.g., 2025-12-09)
/*
INSERT INTO subscription_instances 
(org_id, plan_id, stripe_subscription_id, status, current_period_start, current_period_end, created_at, updated_at)
VALUES 
({org_id}, {plan_id}, 'sub_xxxxx', 'active', 
 '{stripe_current_period_start}'::timestamp,  -- e.g., '2025-11-10 00:00:00'
 '{stripe_current_period_end}'::timestamp,    -- e.g., '2025-12-09 23:59:59'
 NOW(), NOW());

-- Get subscription_id from above insert, then create usage record
INSERT INTO subscription_usage
(subscription_id, org_id, month_start, month_end, word_allowance, words_used, created_at, updated_at)
VALUES
({subscription_id}, {org_id}, 
 '{stripe_current_period_start}'::date,  -- Same as subscription instance
 '{stripe_current_period_end}'::date,    -- Same as subscription instance
 30000,  -- Or 75000 for Team
 0, 
 NOW(), NOW());
*/

-- WARNING: Do NOT use calendar months like '2025-11-01'!
-- Always copy dates exactly from Stripe Dashboard for each subscription

-- Step 4: For subscriptions in database but cancelled in Stripe:
/*
UPDATE subscription_instances
SET status = 'cancelled', updated_at = NOW()
WHERE stripe_subscription_id = 'sub_xxxxx';
*/


-- ============================================
-- NOTES
-- ============================================

-- Always trust Stripe as the source of truth
-- If database and Stripe don't match, update database to match Stripe
-- Keep these scripts handy for daily/weekly operations
-- Add new custom scripts as needed for your specific use cases

-- Last Updated: November 10, 2025
