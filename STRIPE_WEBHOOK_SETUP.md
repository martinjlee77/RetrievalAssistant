# Stripe Webhook Configuration Guide

## Overview
This document provides instructions for configuring Stripe webhooks in production to handle subscription lifecycle events for VeritasLogic.ai.

## Webhook Endpoint

**Production URL:** `https://www.veritaslogic.ai/api/webhooks/stripe`

## Required Webhook Events

Configure the following 3 webhook events in your Stripe Dashboard:

| Event | Purpose | Handler Function |
|-------|---------|-----------------|
| `customer.subscription.updated` | Trial→Professional auto-conversion, plan changes, renewals | `handle_subscription_updated()` |
| `invoice.payment_succeeded` | Reactivate past_due subscriptions after successful payment | `handle_payment_succeeded()` |
| `customer.subscription.deleted` | Mark subscription as cancelled when user cancels | `handle_subscription_deleted()` |

## Setup Instructions

### 1. Access Stripe Dashboard
1. Log in to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Navigate to **Developers** → **Webhooks**
3. Click **Add endpoint**

### 2. Configure Endpoint
- **Endpoint URL:** `https://www.veritaslogic.ai/api/webhooks/stripe`
- **Description:** VeritasLogic Subscription Management
- **Events to send:**
  - `customer.subscription.updated`
  - `invoice.payment_succeeded`
  - `customer.subscription.deleted`

### 3. Get Webhook Signing Secret
1. After creating the endpoint, click on it to view details
2. Copy the **Signing secret** (starts with `whsec_...`)
3. Add to environment variables as `STRIPE_WEBHOOK_SECRET`

### 4. Environment Variables
Ensure the following environment variables are set in production:

```bash
STRIPE_SECRET_KEY=sk_live_...          # Stripe API secret key
STRIPE_WEBHOOK_SECRET=whsec_...        # Webhook signing secret
DATABASE_URL=postgresql://...           # Production database connection
```

## Business Logic Implementation

### Trial → Professional (Auto-conversion)
**Trigger:** `customer.subscription.updated` when status changes from `trialing` to `active`
**Behavior:**
- Deletes trial usage record
- Creates new Professional usage record with full 30,000 words
- Aligns to Stripe billing period (current_period_start/end)

### Professional → Team (Manual upgrade)
**Trigger:** User clicks upgrade in dashboard → `/api/subscription/verify-upgrade` endpoint
**Behavior:**
- Calculates remaining Professional words: `30,000 - words_used`
- Creates Team usage record: `75,000 + remaining_pro_words`
- Preserves historical usage data
- **Note:** This is synchronous, NOT webhook-driven

### Monthly Renewals
**Trigger:** `customer.subscription.updated` at start of new billing period
**Behavior:**
- Updates subscription_instances with new current_period_start/end
- Creates new subscription_usage record for new period
- Resets words to 0 (fresh allowance)

### Cancellations
**Trigger:** `customer.subscription.deleted`
**Behavior:**
- Marks subscription_instances status as 'cancelled'
- Preserves usage data for audit trail

## Testing Webhooks

### Test Mode Setup
1. Create a separate webhook endpoint for test mode: `https://staging.veritaslogic.ai/api/webhooks/stripe`
2. Use Stripe test mode keys (`sk_test_...`, `whsec_test_...`)
3. Configure same 3 events

### Stripe CLI Testing (Local Development)
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Forward webhooks to local server
stripe listen --forward-to localhost:3000/api/webhooks/stripe

# Trigger test events
stripe trigger customer.subscription.updated
stripe trigger invoice.payment_succeeded
stripe trigger customer.subscription.deleted
```

### Manual Testing
1. **Trial Conversion:** Wait 14 days or use Stripe CLI to fast-forward time
2. **Pro→Team Upgrade:** Use dashboard upgrade flow with Stripe test cards
3. **Renewal:** Use Stripe Dashboard to manually advance subscription billing
4. **Cancellation:** Cancel subscription via Customer Portal

## Monitoring & Logs

### Webhook Delivery
- Monitor webhook delivery status in Stripe Dashboard → Webhooks → [Your endpoint]
- Check for failed deliveries and retry as needed

### Application Logs
Look for these log messages in production:
```
✅ Subscription upgraded: org={org_id}, plan={plan_key}
Pro→Team rollover: {X} words will carry over (used {Y}/{Z})
Subscription {stripe_sub_id} updated
Payment succeeded for subscription {stripe_sub_id}
Subscription {stripe_sub_id} cancelled
```

### Database Verification
After webhook events, verify:
```sql
-- Check subscription status
SELECT * FROM subscription_instances WHERE org_id = 'xxx';

-- Check usage records (should align with Stripe periods)
SELECT * FROM subscription_usage WHERE org_id = 'xxx' ORDER BY created_at DESC;

-- Verify word allowances
SELECT su.month_start, su.month_end, su.word_allowance, su.words_used, sp.plan_key
FROM subscription_usage su
JOIN subscription_instances si ON su.subscription_id = si.id
JOIN subscription_plans sp ON si.plan_id = sp.id
WHERE su.org_id = 'xxx'
ORDER BY su.created_at DESC;
```

## Troubleshooting

### Webhook Not Received
1. Check endpoint URL is correct and accessible
2. Verify webhook secret in environment variables
3. Check Stripe Dashboard for delivery attempts and errors
4. Ensure production server is running and port is open

### Signature Verification Failed
- Ensure `STRIPE_WEBHOOK_SECRET` matches the signing secret from Stripe Dashboard
- Check webhook signature validation logic in `stripe_subscription_webhook()` function

### Duplicate Active Subscriptions
- This should never happen with current implementation
- If it does, check logs for failed cancellation queries
- Manually cancel duplicate via SQL:
  ```sql
  UPDATE subscription_instances 
  SET status = 'cancelled' 
  WHERE id = {old_sub_id};
  ```

### Missing Usage Records
- Webhooks create usage records automatically
- If missing, manually create via:
  ```sql
  INSERT INTO subscription_usage (subscription_id, org_id, month_start, month_end, word_allowance, words_used)
  VALUES (...);
  ```

## Security Considerations

1. **Always verify webhook signatures** - Protects against spoofed webhook events
2. **Use HTTPS** - Webhook endpoint must use HTTPS in production
3. **Keep webhook secret secure** - Never commit to version control
4. **Monitor for anomalies** - Watch for unexpected subscription states

## Rollback Plan

If webhooks cause issues in production:

1. **Disable webhooks** in Stripe Dashboard (don't delete, just disable)
2. **Manual subscription management** via Stripe Dashboard
3. **Database cleanup** - Manually update subscription_instances and subscription_usage
4. **Re-enable after fix** - Test in staging first

## Production Checklist

- [ ] Webhook endpoint configured in Stripe Dashboard
- [ ] All 3 events enabled (subscription.updated, payment.succeeded, subscription.deleted)
- [ ] Webhook signing secret added to environment variables
- [ ] Test webhook delivery with Stripe CLI or test mode
- [ ] Verify logs show successful webhook processing
- [ ] Database records align with Stripe billing periods
- [ ] Pro→Team rollover tested and working
- [ ] Historical usage data preserved after upgrades
- [ ] Monitor first 24 hours for any anomalies

---

**Last Updated:** November 10, 2025  
**Version:** 1.0
