# Subscription Lifecycle Testing Plan

## Overview
This document outlines the testing procedures for verifying the complete subscription lifecycle implementation, including webhooks, rollover logic, and Stripe billing period alignment.

## Testing Environment

### Stripe Test Mode
- Use Stripe test mode keys: `sk_test_...`, `pk_test_...`
- Configure test webhook endpoint: `https://staging.veritaslogic.ai/api/webhooks/stripe`
- Use Stripe test credit cards (e.g., `4242 4242 4242 4242`)

### Database Setup
- Use separate test/staging database
- Ensure fresh state for each test run
- Keep production database isolated

## Test Scenarios

### Test 1: Trial Signup → Professional Auto-Conversion

**Objective:** Verify trial converts to Professional after 14 days with full 30K words

**Steps:**
1. Create new user account
2. Sign up for trial (14-day, 9K words)
3. Verify trial subscription created in database:
   ```sql
   SELECT * FROM subscription_instances WHERE org_id = 'xxx';
   -- Should show status='trialing'
   ```
4. Verify trial usage record created:
   ```sql
   SELECT * FROM subscription_usage WHERE org_id = 'xxx';
   -- Should show word_allowance=9000, words_used=0
   ```
5. **Option A: Wait 14 days** (real-time test)
6. **Option B: Use Stripe CLI** to fast-forward trial period:
   ```bash
   stripe fixtures advance subscription_id --trial-end now
   ```
7. Verify webhook received: `customer.subscription.updated` with status change
8. Check database after webhook:
   ```sql
   SELECT * FROM subscription_instances WHERE org_id = 'xxx';
   -- Should show status='active'
   
   SELECT * FROM subscription_usage WHERE org_id = 'xxx' ORDER BY created_at DESC LIMIT 1;
   -- Should show word_allowance=30000, words_used=0
   -- month_start/month_end should match Stripe current_period_start/end
   ```
9. Verify trial usage record was deleted (or marked inactive)
10. Check application logs for: `"Subscription {sub_id} updated"`

**Expected Results:**
- ✅ Trial subscription converts to Professional
- ✅ Usage record shows 30,000 words
- ✅ Billing period aligns with Stripe (NOT calendar month)
- ✅ Trial usage ignored (user gets full 30K)

---

### Test 2: Professional → Team Upgrade with Rollover

**Objective:** Verify Pro→Team upgrade carries over unused words

**Setup:**
- User has active Professional plan (30K words)
- User has used 8,500 words (21,500 remaining)

**Steps:**
1. Set up Professional subscription with partial usage:
   ```sql
   UPDATE subscription_usage 
   SET words_used = 8500 
   WHERE subscription_id = (
       SELECT id FROM subscription_instances WHERE org_id = 'xxx' AND status = 'active'
   );
   ```
2. Navigate to dashboard as logged-in user
3. Click "Upgrade to Team" button
4. Complete Stripe checkout (use test card `4242 4242 4242 4242`)
5. Verify checkout success redirect
6. Check application logs for:
   ```
   Pro→Team rollover: 21500 words will carry over (used 8500/30000)
   ✅ Subscription upgraded: org={org_id}, plan=team
   Cancelled old subscription {old_sub_id}
   ```
7. Verify database changes:
   ```sql
   -- Old Professional subscription should be cancelled
   SELECT * FROM subscription_instances WHERE org_id = 'xxx' ORDER BY created_at DESC;
   -- Should show old sub with status='cancelled', new sub with status='active'
   
   -- Team usage record should show rollover
   SELECT * FROM subscription_usage WHERE org_id = 'xxx' ORDER BY created_at DESC LIMIT 1;
   -- Should show word_allowance=96500 (75000 + 21500)
   -- Should show words_used=0
   -- month_start/month_end should match NEW Stripe billing period
   ```
8. Verify historical data preserved:
   ```sql
   SELECT * FROM subscription_usage WHERE org_id = 'xxx' ORDER BY created_at DESC;
   -- Should show BOTH old Professional record (8500/30000) AND new Team record (0/96500)
   ```
9. Test edge case: Upgrade with 0 remaining words
   - Set `words_used = 30000` in Professional record
   - Run upgrade again
   - Verify Team allowance = 75,000 (no negative rollover)

**Expected Results:**
- ✅ Remaining Pro words carried over to Team allowance
- ✅ Math correct: 75,000 + 21,500 = 96,500
- ✅ Historical Professional usage preserved (not deleted)
- ✅ Billing period aligned to NEW subscription start date
- ✅ Old subscription marked as cancelled

---

### Test 3: Professional → Team Upgrade (No Prior Usage Record)

**Objective:** Verify upgrade works even if usage record is missing

**Setup:**
1. Create Professional subscription WITHOUT usage record:
   ```sql
   INSERT INTO subscription_instances (org_id, plan_id, stripe_subscription_id, status, current_period_start, current_period_end)
   VALUES (...);
   -- Do NOT create matching subscription_usage record
   ```

**Steps:**
1. Attempt Team upgrade via dashboard
2. Complete Stripe checkout
3. Verify no errors in logs
4. Check database:
   ```sql
   -- Old subscription should still be cancelled
   SELECT * FROM subscription_instances WHERE org_id = 'xxx' ORDER BY created_at DESC;
   
   -- Team usage should be created with standard allowance (no rollover)
   SELECT * FROM subscription_usage WHERE org_id = 'xxx' ORDER BY created_at DESC LIMIT 1;
   -- Should show word_allowance=75000 (no rollover since no prior usage found)
   ```

**Expected Results:**
- ✅ Upgrade succeeds despite missing usage record
- ✅ Old subscription cancelled (prevents duplicate active subscriptions)
- ✅ Team allowance = 75,000 (standard, no rollover)
- ✅ No errors or crashes

---

### Test 4: Monthly Renewal (Professional Plan)

**Objective:** Verify word allowance resets on renewal

**Setup:**
- User has Professional plan with 15,000 words used
- Billing cycle ends tomorrow

**Steps:**
1. Wait for natural billing cycle renewal OR use Stripe CLI:
   ```bash
   stripe trigger customer.subscription.updated --stripe-account xxx
   ```
2. Verify webhook `customer.subscription.updated` received
3. Check database after renewal:
   ```sql
   SELECT * FROM subscription_usage WHERE org_id = 'xxx' ORDER BY created_at DESC LIMIT 2;
   -- Should show TWO records:
   -- Old period: word_allowance=30000, words_used=15000
   -- New period: word_allowance=30000, words_used=0
   ```
4. Verify billing periods don't overlap:
   - Old period: month_end = 2025-12-09
   - New period: month_start = 2025-12-10
5. Check Stripe alignment:
   - Fetch subscription from Stripe API
   - Compare `current_period_start` and `current_period_end` with database `month_start`/`month_end`
   - Should match exactly (date conversion accounts for timezone)

**Expected Results:**
- ✅ New usage record created for new billing period
- ✅ Word allowance reset to 30,000
- ✅ Previous period's usage preserved (15,000/30,000)
- ✅ Billing periods align with Stripe (NOT calendar months)

---

### Test 5: Subscription Cancellation

**Objective:** Verify cancellation marks subscription correctly

**Steps:**
1. User navigates to Stripe Customer Portal
2. Click "Cancel subscription"
3. Confirm cancellation
4. Verify webhook `customer.subscription.deleted` received
5. Check database:
   ```sql
   SELECT * FROM subscription_instances WHERE org_id = 'xxx';
   -- Should show status='cancelled'
   ```
6. Verify usage data still accessible (not deleted)
7. Attempt to run analysis with cancelled subscription
8. Should receive error: "Subscription required"

**Expected Results:**
- ✅ Subscription marked as cancelled
- ✅ Usage history preserved for audit trail
- ✅ User cannot run new analyses

---

### Test 6: Payment Failure → Past Due → Recovery

**Objective:** Verify subscription status updates on payment failures

**Steps:**
1. Configure Stripe test card to fail: `4000 0000 0000 0341` (charge declined)
2. Wait for renewal attempt
3. Verify webhook `invoice.payment_failed` received
4. Check database:
   ```sql
   SELECT * FROM subscription_instances WHERE org_id = 'xxx';
   -- Should show status='past_due'
   ```
5. Update payment method to valid card: `4242 4242 4242 4242`
6. Trigger retry or wait for Stripe auto-retry
7. Verify webhook `invoice.payment_succeeded` received
8. Check database:
   ```sql
   SELECT * FROM subscription_instances WHERE org_id = 'xxx';
   -- Should show status='active' (reactivated)
   ```

**Expected Results:**
- ✅ Subscription marked as past_due on failure
- ✅ Subscription reactivated on successful payment
- ✅ Usage allowance preserved during past_due period

---

### Test 7: Complete Lifecycle (End-to-End)

**Objective:** Test full user journey from trial to Team

**Steps:**
1. **Trial Signup:**
   - Create account
   - Verify 9K trial allowance
2. **Use Trial Words:**
   - Run analysis consuming 3,500 words
   - Verify words_used updated in database
3. **Trial → Pro Conversion:**
   - Wait 14 days or use Stripe CLI to advance
   - Verify full 30K Professional allowance (trial usage ignored)
4. **Use Professional Words:**
   - Run analyses consuming 8,500 words
   - Verify 21,500 remaining
5. **Pro → Team Upgrade:**
   - Click upgrade, complete checkout
   - Verify 96,500 Team allowance (75K + 21.5K rollover)
6. **Use Team Words:**
   - Run large analysis consuming 50,000 words
   - Verify 46,500 remaining
7. **Monthly Renewal:**
   - Advance to next billing cycle
   - Verify allowance reset to 75,000 (standard Team)
8. **Cancellation:**
   - Cancel via Customer Portal
   - Verify subscription marked cancelled
   - Verify cannot run new analyses

**Expected Results:**
- ✅ Complete lifecycle works end-to-end
- ✅ All word calculations correct at each stage
- ✅ Billing periods align with Stripe throughout
- ✅ Historical data preserved at all stages

---

## Automated Testing (Future Enhancement)

### Unit Tests
```python
# tests/test_subscription_webhooks.py
def test_trial_to_professional_conversion():
    """Test webhook handler for trial → Professional conversion"""
    # Mock Stripe webhook event
    # Call handle_subscription_updated()
    # Assert usage record created with 30K words

def test_pro_to_team_rollover():
    """Test Professional → Team upgrade with rollover"""
    # Create Pro usage with 8,500 used
    # Call verify_and_process_upgrade()
    # Assert Team allowance = 96,500

def test_monthly_renewal():
    """Test word allowance reset on renewal"""
    # Create usage with words_used > 0
    # Call handle_subscription_updated() with new period
    # Assert new usage record with words_used = 0
```

### Integration Tests
```python
# tests/test_stripe_integration.py
def test_stripe_checkout_flow():
    """Test full Stripe checkout and webhook delivery"""
    # Use Stripe test mode
    # Create checkout session
    # Simulate webhook event
    # Verify database state
```

---

## Regression Testing Checklist

Before each production deployment:

- [ ] Trial → Pro conversion tested (full 30K words)
- [ ] Pro → Team upgrade tested (rollover math correct)
- [ ] Pro → Team upgrade tested without usage record (no crash)
- [ ] Monthly renewal tested (word reset, Stripe period alignment)
- [ ] Cancellation tested (status updated, data preserved)
- [ ] Payment failure → recovery tested (past_due → active)
- [ ] Historical usage data preserved after all upgrades
- [ ] No duplicate active subscriptions created
- [ ] All billing periods align with Stripe (NOT calendar months)
- [ ] Webhook logs show successful processing
- [ ] Database queries match expected state

---

## Monitoring After Deployment

### Week 1: Intensive Monitoring
- Check webhook delivery success rate (target: >99.9%)
- Monitor for any 500 errors on webhook endpoint
- Verify all subscription updates create usage records
- Check for any duplicate active subscriptions
- Monitor rollover calculations (should match user expectations)

### Ongoing Monitoring
- Weekly review of subscription_usage alignment with Stripe
- Monthly audit of historical usage data integrity
- Quarterly review of webhook failure logs

---

**Last Updated:** November 10, 2025  
**Version:** 1.0
