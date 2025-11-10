# Stripe Production Migration Checklist

**CRITICAL**: Follow this checklist when moving from Stripe Test Mode to Production Mode

---

## ⚠️ Pre-Migration Requirements

### 1. **Stripe Account Setup**
- [ ] Activate your Stripe account (complete verification, business info, banking details)
- [ ] Switch Stripe Dashboard from "Test Mode" to "Live Mode" toggle (top right)

### 2. **Production API Keys**
- [ ] In Stripe Dashboard → Developers → API keys → Live mode:
  - [ ] Copy **Publishable key** (starts with `pk_live_`)
  - [ ] Copy **Secret key** (starts with `sk_live_`)

---

## 🔧 Code Changes Required

### 1. **Update Environment Variables**
Update in Railway Project: **virtuous-charisma** (Backend/Worker/Redis)

```bash
# OLD (Test Mode):
STRIPE_API_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...  # You'll get a NEW one for production

# NEW (Production Mode):
STRIPE_API_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...  # NEW webhook secret (see step 3)
```

**⚠️ IMPORTANT**: The webhook secret WILL change. You'll get a new one after setting up production webhooks (Step 3 below).

---

### 2. **Update Stripe Price IDs**
File: `backend_api.py` (lines ~213-255)

You need to **create new products/prices in Live Mode** and update these IDs:

```python
# CURRENT (Test Mode):
SUBSCRIPTION_PLANS = {
    'trial': {
        'name': 'Trial',
        'price_monthly': 0,
        'word_allowance': 9000,
        'stripe_price_id': None  # No Stripe price for trial
    },
    'professional': {
        'name': 'Professional',
        'price_monthly': 295,
        'word_allowance': 30000,
        'stripe_price_id': 'price_TEST_ID_HERE'  # ← UPDATE THIS
    },
    'team': {
        'name': 'Team',
        'price_monthly': 595,
        'word_allowance': 75000,
        'stripe_price_id': 'price_TEST_ID_HERE'  # ← UPDATE THIS
    },
    'enterprise': {
        'name': 'Enterprise',
        'price_monthly': 1195,
        'word_allowance': 180000,
        'stripe_price_id': 'price_TEST_ID_HERE'  # ← UPDATE THIS
    }
}
```

#### How to Get Production Price IDs:
1. In Stripe Dashboard (Live Mode) → Products
2. Create products for each plan:
   - **Professional**: $295/month, recurring
   - **Team**: $595/month, recurring
   - **Enterprise**: $1,195/month, recurring
3. Copy each price ID (starts with `price_`) and update the code above
4. Deploy updated code to Railway

---

### 3. **Configure Production Webhooks**
Webhooks handle subscription updates automatically (renewals, cancellations, etc.)

#### Setup Steps:
1. In Stripe Dashboard (Live Mode) → Developers → Webhooks
2. Click "+ Add endpoint"
3. **Endpoint URL**: `https://your-railway-backend-url.railway.app/api/webhooks/stripe`
   - Replace with your actual Railway backend URL from **virtuous-charisma** project
4. **Events to listen for**:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Click "Add endpoint"
6. Click on the new endpoint → "Signing secret" → Copy it
7. Update `STRIPE_WEBHOOK_SECRET` in Railway with the new production secret

---

### 4. **Update Dashboard Stripe.js (Frontend)**
File: `veritaslogic_multipage_website/dashboard.html`

Find the Stripe.js initialization (search for `Stripe(`) and verify it's using the publishable key from environment:

```javascript
// Should already be dynamic, but verify:
const stripe = Stripe('pk_live_...');  // Will use production key automatically
```

**No code changes needed** if you're loading the key from backend API.

---

## 🧪 Testing Checklist (Production)

### Before Going Live:
- [ ] Test signup flow with **real credit card** (will charge real money)
- [ ] Verify subscription appears in Stripe Dashboard (Live Mode) → Customers
- [ ] Verify subscription_instances table updated correctly in production database
- [ ] Test upgrade flow (Trial → Professional)
- [ ] Test subscription cancellation
- [ ] Verify webhook events are received (check Stripe Dashboard → Webhooks → Events)

### Test with Caution:
⚠️ **Real charges will occur!** Use your own card for testing, then cancel/refund.

---

## 📋 Final Verification

- [ ] All test mode keys removed from environment variables
- [ ] All production API keys added to Railway
- [ ] All Stripe price IDs updated to live mode IDs
- [ ] Production webhook endpoint configured and verified
- [ ] Webhook secret updated in environment variables
- [ ] Test signup completed successfully (real charge)
- [ ] Database records created correctly
- [ ] Dashboard displays correct subscription info
- [ ] Webhook events processing correctly (check Stripe logs)

---

## 🚨 Common Mistakes to Avoid

1. **Mixing test/live keys**: Never mix `sk_test_` with `pk_live_` or vice versa
2. **Forgetting webhook secret**: Production webhooks have a DIFFERENT secret than test mode
3. **Using test price IDs**: Test mode price IDs (`price_1ABC...`) won't work in production
4. **Not testing webhooks**: Webhooks can fail silently - always check Stripe Dashboard → Webhooks → Events
5. **Wrong Railway project**: Update environment variables in **virtuous-charisma**, not desirable-purpose

---

## 🔄 Rollback Plan (If Issues Occur)

If you need to rollback to test mode:

1. Switch Stripe Dashboard back to "Test Mode"
2. Update Railway environment variables back to test keys
3. Update `stripe_price_id` values back to test IDs
4. Redeploy backend
5. Update webhook URL to point to test mode endpoint (or disable)

---

## 📞 Support Resources

- **Stripe Dashboard**: https://dashboard.stripe.com
- **Stripe Docs**: https://stripe.com/docs
- **Test Cards**: https://stripe.com/docs/testing (for debugging)
- **Railway Logs**: Check backend logs for Stripe API errors

---

**Last Updated**: November 2025  
**Migration Status**: ⏳ In Sandbox Mode

When you complete the migration, update the status above to: ✅ Production Mode Active
