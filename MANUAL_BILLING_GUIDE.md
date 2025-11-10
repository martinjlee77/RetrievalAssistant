# Manual Billing Workflow for VeritasLogic.ai

## Overview
For a small number of enterprise customers (Big 4 firms, large accounting teams), manual subscription management is simpler, more reliable, and easier to troubleshoot than automated webhooks.

**Who this is for:** Platforms with <50 customers where manual intervention is faster than debugging automation.

## ⚠️ CRITICAL: Stripe Billing Periods vs Calendar Months

**ALWAYS use Stripe's actual billing dates**, not calendar months!

❌ **WRONG:** `month_start = '2025-11-01'` (first of calendar month)  
✅ **CORRECT:** `month_start = current_period_start::date` (Stripe's billing start)

**Why this matters:**
- Customer signs up on Nov 10 → billing period is Nov 10 - Dec 9 (NOT Nov 1 - Nov 30)
- If you use calendar months, word allowances get out of sync with Stripe billing
- Customer gets charged but database shows wrong allowance → broken experience

**Solution:** Every SQL script in this guide uses Stripe's `current_period_start` and `current_period_end` dates from the `subscription_instances` table.

## Your Current Setup (Keep This)

✅ **What Works:**
- Stripe Checkout for trial signups
- Stripe Checkout for upgrades (Pro→Team)
- Stripe Customer Portal for payment management
- Database tracks subscriptions and word usage
- Word deduction happens automatically during analysis

❌ **What You DON'T Need:**
- Webhook endpoints
- Automated trial conversions
- Automated renewal processing
- Complex event handling

## Daily/Weekly Routine

### Check Stripe Dashboard (5 minutes/day)
1. Log in to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Navigate to **Customers**
3. Look for:
   - New trial signups (filter by "Trialing")
   - Upcoming renewals (filter by "Active")
   - Failed payments (filter by "Past Due")
   - Cancellations (filter by "Canceled")

---

## Common Operations

### Operation 1: New Trial Signup

**What happens automatically:**
- ✅ User creates account
- ✅ Stripe checkout creates subscription (14-day trial)
- ✅ Database records subscription via `/api/subscription/verify-upgrade`

**What you do:** Nothing! The checkout already created the database records.

**Verify (optional):**
```sql
-- Check trial was created
SELECT u.email, si.status, su.word_allowance, su.words_used
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
WHERE u.email = 'customer@bigfour.com';
-- Should show: status='trialing', word_allowance=9000
```

---

### Operation 2: Trial → Professional Conversion (Day 14)

**When Stripe charges the customer:**
You'll get an email from Stripe: "New payment received"

**Manual steps (2 minutes):**

1. **Find the customer in database:**
   ```sql
   SELECT u.id, u.email, u.org_id, si.id as sub_id, si.stripe_subscription_id
   FROM users u
   JOIN subscription_instances si ON si.org_id = u.org_id
   WHERE u.email = 'customer@bigfour.com' AND si.status = 'trialing';
   ```

2. **Update subscription status:**
   ```sql
   -- Change status from 'trialing' to 'active'
   UPDATE subscription_instances
   SET status = 'active', updated_at = NOW()
   WHERE id = {sub_id_from_above};
   ```

3. **Get Stripe billing period:**
   ```sql
   -- Get the actual billing dates from Stripe (NOT calendar month!)
   SELECT 
       current_period_start::date as billing_start,
       current_period_end::date as billing_end
   FROM subscription_instances
   WHERE id = {sub_id_from_above};
   -- Copy these dates for next step
   ```

4. **Update word allowance to Professional (30K) with Stripe billing period:**
   ```sql
   -- Update usage record with Professional allowance AND Stripe billing dates
   UPDATE subscription_usage
   SET word_allowance = 30000, 
       words_used = 0,  -- Reset usage (ignore trial words)
       month_start = '{billing_start}',  -- From step 3, e.g., '2025-11-10'
       month_end = '{billing_end}',      -- From step 3, e.g., '2025-12-09'
       updated_at = NOW()
   WHERE subscription_id = {sub_id_from_above};
   ```

5. **Verify:**
   ```sql
   SELECT u.email, si.status, su.word_allowance, su.words_used
   FROM users u
   JOIN subscription_instances si ON si.org_id = u.org_id
   JOIN subscription_usage su ON su.subscription_id = si.id
   WHERE u.email = 'customer@bigfour.com';
   -- Should show: status='active', word_allowance=30000, words_used=0
   ```

**Done!** Customer now has full Professional access.

---

### Operation 3: Professional → Team Upgrade

**What happens automatically:**
- ✅ User clicks "Upgrade to Team" in dashboard
- ✅ Stripe checkout processes payment
- ✅ `/api/subscription/verify-upgrade` endpoint handles everything:
  - Cancels old Professional subscription
  - Creates new Team subscription
  - **Automatically calculates rollover:** 75,000 + remaining Pro words

**What you do:** Nothing! The upgrade endpoint already handles rollover logic.

**Verify rollover worked (optional):**
```sql
-- Check Team subscription was created with rollover
SELECT u.email, si.status, su.word_allowance, su.words_used, sp.plan_key
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE u.email = 'customer@bigfour.com' AND si.status = 'active';
-- Should show: plan_key='team', word_allowance=96500 (if they had 21.5K Pro words left)
```

---

### Operation 4: Monthly Renewal (Reset Word Allowance)

**When Stripe charges monthly renewal:**
You'll get an email from Stripe: "Recurring payment succeeded"

**Manual steps (1 minute):**

1. **Find active subscription:**
   ```sql
   SELECT u.email, si.id as sub_id, sp.plan_key, su.word_allowance, su.words_used
   FROM users u
   JOIN subscription_instances si ON si.org_id = u.org_id
   JOIN subscription_usage su ON su.subscription_id = si.id
   JOIN subscription_plans sp ON si.plan_id = sp.id
   WHERE u.email = 'customer@bigfour.com' AND si.status = 'active';
   ```

2. **Get NEW Stripe billing period:**
   ```sql
   -- IMPORTANT: Use Stripe's billing dates, NOT calendar month!
   SELECT 
       current_period_start::date as new_billing_start,
       current_period_end::date as new_billing_end
   FROM subscription_instances
   WHERE id = {sub_id_from_above};
   -- Copy these dates for next step
   ```

3. **Reset word allowance with Stripe billing period:**
   ```sql
   -- Professional: Reset to 30K (Team: verify word_allowance = 75000)
   UPDATE subscription_usage
   SET words_used = 0,
       month_start = '{new_billing_start}',  -- From step 2, e.g., '2025-12-10'
       month_end = '{new_billing_end}',      -- From step 2, e.g., '2026-01-09'
       updated_at = NOW()
   WHERE subscription_id = {sub_id_from_above};
   ```

4. **Verify:**
   ```sql
   SELECT u.email, su.word_allowance, su.words_used, su.month_start, su.month_end,
          si.current_period_start::date as stripe_start
   FROM users u
   JOIN subscription_instances si ON si.org_id = u.org_id
   JOIN subscription_usage su ON su.subscription_id = si.id
   WHERE u.email = 'customer@bigfour.com';
   -- Should show: words_used=0, month_start matches stripe_start (Stripe billing period)
   ```

**Done!** Customer has fresh monthly allowance.

---

### Operation 5: Payment Failed → Past Due

**When Stripe payment fails:**
You'll get an email from Stripe: "Payment failed"

**Manual steps (30 seconds):**

1. **Mark subscription as past_due:**
   ```sql
   UPDATE subscription_instances
   SET status = 'past_due', updated_at = NOW()
   WHERE stripe_subscription_id = '{stripe_sub_id_from_email}';
   ```

2. **Stripe automatically retries** - Wait for retry or customer updates payment method

3. **When payment succeeds, mark active again:**
   ```sql
   UPDATE subscription_instances
   SET status = 'active', updated_at = NOW()
   WHERE stripe_subscription_id = '{stripe_sub_id}';
   ```

---

### Operation 6: Customer Cancels Subscription

**When customer cancels via Stripe Customer Portal:**
You'll get an email from Stripe: "Subscription canceled"

**Manual steps (30 seconds):**

```sql
-- Mark subscription as cancelled
UPDATE subscription_instances
SET status = 'cancelled', updated_at = NOW()
WHERE stripe_subscription_id = '{stripe_sub_id_from_email}';
```

**Note:** Customer retains access until end of current billing period (Stripe handles this automatically).

---

## Quick Reference SQL Scripts

### Script 1: Check All Active Subscriptions
```sql
SELECT 
    u.email,
    sp.plan_key,
    si.status,
    su.word_allowance,
    su.words_used,
    (su.word_allowance - su.words_used) as remaining,
    su.month_start,
    su.month_end,
    si.stripe_subscription_id
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE si.status IN ('active', 'trialing')
ORDER BY u.email;
```

### Script 2: Find Customer by Email
```sql
SELECT 
    u.id as user_id,
    u.email,
    u.org_id,
    si.id as subscription_id,
    si.stripe_subscription_id,
    si.status,
    sp.plan_key,
    su.word_allowance,
    su.words_used
FROM users u
LEFT JOIN subscription_instances si ON si.org_id = u.org_id
LEFT JOIN subscription_usage su ON su.subscription_id = si.id
LEFT JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE u.email = 'customer@example.com'
ORDER BY si.created_at DESC
LIMIT 5;
```

### Script 3: Upcoming Renewals (This Month)
```sql
SELECT 
    u.email,
    sp.plan_key,
    su.month_end as renewal_date,
    su.words_used,
    su.word_allowance
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE si.status = 'active'
  AND su.month_end BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY su.month_end;
```

### Script 4: Customers Near Word Limit (>90% used)
```sql
SELECT 
    u.email,
    sp.plan_key,
    su.word_allowance,
    su.words_used,
    ROUND((su.words_used::numeric / su.word_allowance * 100), 1) as pct_used
FROM users u
JOIN subscription_instances si ON si.org_id = u.org_id
JOIN subscription_usage su ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE si.status = 'active'
  AND (su.words_used::numeric / su.word_allowance) > 0.9
ORDER BY pct_used DESC;
```

---

## Stripe Dashboard Quick Checks

### Daily Check (1 minute)
1. Go to Stripe → **Payments**
2. Look for new payments in last 24 hours
3. If you see new payments, verify database was updated

### Weekly Check (5 minutes)
1. Go to Stripe → **Customers** → Filter: "Active"
2. Count active subscriptions
3. Run SQL Script 1 above
4. Numbers should match

### Monthly Check (10 minutes)
1. Export customer list from Stripe
2. Export active subscriptions from database (Script 1)
3. Compare for discrepancies
4. Fix any mismatches manually

---

## When to Consider Webhooks

You should add automated webhooks when:
- [ ] You have >50 active customers
- [ ] Manual updates take >30 min/week
- [ ] You're missing renewals/conversions
- [ ] You hire someone to manage billing

Until then, manual is simpler and more reliable.

---

## Troubleshooting

### Customer says "I upgraded but still see Professional"
1. Check Stripe: Did payment succeed?
2. Check database: Run Script 2 (find by email)
3. If payment succeeded but database not updated, run Operation 3 manually

### Customer says "My words didn't reset this month"
1. Check Stripe: Did monthly payment succeed?
2. Check database: Run Script 2
3. If payment succeeded, run Operation 4 manually

### Stripe and Database Don't Match
1. Always trust Stripe as source of truth
2. Update database to match Stripe
3. Use scripts above to sync

---

## Backup Plan: Full Database Reset (Emergency Only)

If everything gets out of sync:

```sql
-- WARNING: Only use this if you need to completely resync with Stripe
-- Step 1: Backup database first!
-- Step 2: Export all active subscriptions from Stripe Dashboard

-- Step 3: For each customer, get their Stripe billing period:
-- Log into Stripe → Customers → Click customer → View subscription
-- Copy current_period_start and current_period_end dates

-- Step 4: Cancel old database records
UPDATE subscription_instances SET status = 'cancelled';

-- Step 5: Rebuild using Stripe data (MUST use Stripe billing dates!)
-- For each customer, replace placeholders with ACTUAL Stripe values:
-- {org_id} - from database
-- {plan_id} - from subscription_plans table
-- {stripe_sub_id} - from Stripe Dashboard (e.g., 'sub_xxxxx')
-- {stripe_billing_start} - current_period_start from Stripe (e.g., '2025-11-10')
-- {stripe_billing_end} - current_period_end from Stripe (e.g., '2025-12-09')
-- {word_allowance} - 30000 (Pro) or 75000 (Team)

-- WARNING: NEVER use calendar months like '2025-11-01'! Always use Stripe dates!
-- ❌ WRONG: month_start = '2025-11-01' (calendar month)
-- ✅ CORRECT: month_start = '2025-11-10' (Stripe current_period_start)

-- After you have all the Stripe data, run the manual operation scripts (Operation 1-6)
-- to rebuild each customer subscription properly.
```

---

**Bottom Line:**
For <50 customers, spending 5-10 minutes/week on manual billing is way simpler than debugging webhooks. You can always add automation later if you scale up.

---

**Last Updated:** November 10, 2025  
**Version:** 1.0 (Manual Billing)
