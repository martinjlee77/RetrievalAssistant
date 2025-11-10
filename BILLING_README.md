# VeritasLogic.ai - Billing System Overview

## Current Approach: Manual Billing ✅

For a small number of enterprise customers (<50), we use **manual subscription management** instead of automated webhooks.

### Why Manual?

- **Simpler:** No webhook debugging, no race conditions
- **More Reliable:** Direct control over every subscription change
- **Faster:** 2-5 minutes per operation vs hours debugging automation
- **Better for Enterprise:** Personal touch for Big 4 clients

### Daily Workflow (5-10 min/week)

1. Check Stripe Dashboard for new events (payments, cancellations)
2. Run SQL scripts from `admin_sql_scripts.sql` to update database
3. Done!

## Key Documents

### Primary (Use These)
- **`MANUAL_BILLING_GUIDE.md`** - Complete workflow for all subscription operations
- **`admin_sql_scripts.sql`** - Copy-paste SQL scripts for common tasks

### Optional (Future Automation)
- `docs/optional-automation/STRIPE_WEBHOOK_SETUP.md` - Setup guide if you want webhooks later
- `docs/optional-automation/SUBSCRIPTION_TESTING_PLAN.md` - Testing procedures for automation

## What Works Automatically

✅ **Trial Signups:** Stripe Checkout creates database records automatically  
✅ **Pro→Team Upgrades:** `/api/subscription/verify-upgrade` handles rollover (75K + unused Pro words)  
✅ **Word Deductions:** Analyses deduct words automatically  
✅ **Payment Processing:** Stripe handles all card processing  

## What You Do Manually

🔧 **Trial→Pro Conversion (Day 14):** Run SQL script to update status and word allowance (2 min)  
🔧 **Monthly Renewals:** Run SQL script to reset word count (1 min)  
🔧 **Payment Failures:** Mark as past_due in database (30 sec)  
🔧 **Cancellations:** Mark as cancelled in database (30 sec)  

## Common Operations

### Convert Trial to Professional
```sql
-- See admin_sql_scripts.sql - OPERATION 1
UPDATE subscription_instances SET status = 'active' WHERE ...;
UPDATE subscription_usage SET word_allowance = 15000, words_used = 0 WHERE ...;
```

### Reset Words for Monthly Renewal
```sql
-- See admin_sql_scripts.sql - OPERATION 2
UPDATE subscription_usage SET words_used = 0, month_start = ..., month_end = ... WHERE ...;
```

### Check All Active Customers
```sql
-- See admin_sql_scripts.sql - QUICK CHECK 1
SELECT u.email, sp.plan_key, su.word_allowance, su.words_used ...
```

## When to Add Webhooks

Consider automation when you have:
- [ ] 50+ active customers
- [ ] >30 min/week spent on manual updates
- [ ] Multiple people managing billing
- [ ] Missing renewals/conversions regularly

Until then, manual is faster and simpler.

## Production Database Schema

### subscription_instances
- `org_id` - Links to organization
- `plan_id` - FK to subscription_plans
- `stripe_subscription_id` - Stripe sub ID (e.g., "sub_xxxxx")
- `status` - 'trialing', 'active', 'past_due', 'cancelled'
- `current_period_start` / `current_period_end` - Stripe billing period

### subscription_usage
- `subscription_id` - FK to subscription_instances
- `org_id` - Organization ID
- `month_start` / `month_end` - Usage period (aligned with Stripe billing)
- `word_allowance` - Total words for this period
- `words_used` - Words consumed so far

### Business Rules
- **Trial→Pro:** Full 30K words (ignore trial usage)
- **Pro→Team:** 75K + remaining Pro words (rollover preserved)
- **Monthly Renewal:** Reset words_used to 0
- **Cancellation:** Preserve usage data for audit trail

## Support

For billing questions:
1. Check `MANUAL_BILLING_GUIDE.md`
2. Use scripts from `admin_sql_scripts.sql`
3. Always trust Stripe as source of truth
4. Update database to match Stripe when in doubt

---

**Last Updated:** November 10, 2025  
**Billing System:** Manual (with optional webhook automation for future)
