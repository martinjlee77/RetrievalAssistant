# Railway Environment Variables Checklist

## Critical (Required for Deployment)

### Database
- [ ] `DATABASE_URL` - Auto-configured by Railway PostgreSQL addon

### Redis (Critical for Background Jobs)
- [ ] `REDIS_URL` - Auto-configured by Railway Redis addon
  - **Action:** Verify Redis addon is attached to project

### API Keys
- [ ] `OPENAI_API_KEY` - OpenAI API key for GPT-4o/GPT-5
  - Get from: https://platform.openai.com/api-keys

- [ ] `POSTMARK_API_KEY` - Postmark API for transactional emails
  - Get from: https://account.postmarkapp.com/servers
  - Used for: Email verification, password resets, trial notifications

### Stripe (Payment Processing)
- [ ] `STRIPE_SECRET_KEY` - Stripe secret key (live mode)
  - Get from: https://dashboard.stripe.com/apikeys
  
- [ ] `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key (live mode)
  - Get from: https://dashboard.stripe.com/apikeys
  
- [ ] `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret
  - Get from: https://dashboard.stripe.com/webhooks
  - Endpoint URL: `https://www.veritaslogic.ai/stripe/webhook`

### Security
- [ ] `SECRET_KEY` - JWT signing key (generate random 64-char string)
  - Generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
  - **Never share this value**

---

## Optional (Recommended for Production)

### URLs
- [ ] `WEBSITE_URL` - Marketing website URL
  - Default: `https://www.veritaslogic.ai`
  - Auto-detected if not set

- [ ] `STREAMLIT_URL` - Analysis platform URL
  - Default: `https://tas.veritaslogic.ai`
  - Auto-detected if not set

### Bot Protection
- [ ] `RECAPTCHA_SECRET_KEY` - Google reCAPTCHA secret
  - Get from: https://www.google.com/recaptcha/admin
  - Optional: Signup works without it in dev mode

- [ ] `RECAPTCHA_SITE_KEY` - Google reCAPTCHA site key
  - Get from: https://www.google.com/recaptcha/admin
  - Frontend needs this for signup form

---

## Verification Commands

### Check All Variables Are Set

```bash
# SSH into Railway container or use Railway CLI
railway run env

# Should see all variables listed above
```

### Test Specific Integrations

```bash
# Test OpenAI API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Postmark API key
curl -X POST "https://api.postmarkapp.com/email" \
  -H "X-Postmark-Server-Token: $POSTMARK_API_KEY" \
  -H "Content-Type: application/json"

# Test Stripe API key
curl https://api.stripe.com/v1/customers \
  -u $STRIPE_SECRET_KEY:

# Test Redis connection
railway run redis-cli ping
# Should return: PONG
```

---

## Post-Deployment Validation

After deploying, verify these endpoints work:

```bash
# Check subscription plans endpoint
curl https://www.veritaslogic.ai/api/subscription/plans

# Check reCAPTCHA site key endpoint
curl https://www.veritaslogic.ai/api/recaptcha/site-key

# Check backend health
curl https://www.veritaslogic.ai/api/health
```

---

## Security Notes

1. **Never commit secrets to git**
2. **Use Railway's secret management** - all env vars are encrypted
3. **Rotate keys regularly** - especially SECRET_KEY and Stripe keys
4. **Use different keys** for test vs production environments
5. **Monitor Stripe webhook signatures** - rejects invalid webhooks automatically

---

## Common Issues

### "Invalid Stripe API Key"
- Verify you're using **live mode** keys (not test mode `sk_test_...`)
- Check key hasn't been revoked in Stripe dashboard

### "Postmark API Error 401"
- Verify API token is from correct server
- Check token hasn't expired

### "Redis Connection Refused"
- Verify Redis addon is attached to Railway project
- Check REDIS_URL environment variable is set
- Restart worker service

### "reCAPTCHA verification failed"
- In production: Verify both SECRET_KEY and SITE_KEY are set
- In development: reCAPTCHA is optional (will skip if not configured)

---

Last Updated: November 2025
