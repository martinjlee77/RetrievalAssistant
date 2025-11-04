# Trial Abuse Prevention System - Setup Guide

## Overview
The trial protection system prevents abuse through multiple layers:
1. **Business Email Validation** - Rejects personal email providers (gmail, yahoo, etc.)
2. **reCAPTCHA v3** - Bot detection and suspicious activity prevention
3. **Rate Limiting** - Limits signup attempts per IP and domain
4. **One Trial Per Domain** - Prevents multiple trial signups from same organization

## Environment Variables Required

### reCAPTCHA Configuration
You need to obtain reCAPTCHA v3 keys from Google:

1. Go to https://www.google.com/recaptcha/admin
2. Register a new site:
   - **Label**: VeritasLogic Trial Protection
   - **reCAPTCHA type**: reCAPTCHA v3
   - **Domains**: 
     - veritaslogic.ai
     - www.veritaslogic.ai
     - Add any development domains (localhost, etc.)
3. Copy the keys and add to your environment:

```bash
# Google reCAPTCHA v3 Keys
RECAPTCHA_SITE_KEY=your_site_key_here
RECAPTCHA_SECRET_KEY=your_secret_key_here
```

**Important**: 
- The SITE_KEY is public and used in the frontend
- The SECRET_KEY is private and only used on the backend
- Never commit these keys to git

## Database Schema

The system uses a `signup_attempts` table to track all signup attempts:

```sql
CREATE TABLE IF NOT EXISTS signup_attempts (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    email VARCHAR(255) NOT NULL,
    email_domain VARCHAR(255) NOT NULL,
    success BOOLEAN NOT NULL DEFAULT false,
    failure_reason TEXT,
    attempted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_signup_attempts_ip_time ON signup_attempts(ip_address, attempted_at);
CREATE INDEX IF NOT EXISTS idx_signup_attempts_domain_time ON signup_attempts(email_domain, attempted_at);
CREATE INDEX IF NOT EXISTS idx_signup_attempts_cleanup ON signup_attempts(attempted_at);
```

This table has already been created in the development database.

## Configuration Options

### Rate Limits (in `shared/trial_protection.py`)

```python
RATE_LIMIT_WINDOW_MINUTES = 60  # Time window for rate limiting
MAX_SIGNUP_ATTEMPTS_PER_IP = 3  # Max attempts per IP in window
MAX_SIGNUP_ATTEMPTS_PER_DOMAIN = 2  # Max attempts per domain in window
```

### reCAPTCHA Score Threshold

```python
# reCAPTCHA v3 scores range from 0.0 (bot) to 1.0 (human)
# Current threshold: 0.5 (moderate protection)
if score < 0.5:
    # Block signup
```

You can adjust this threshold based on your fraud rate:
- **0.3** - Lenient (fewer false positives)
- **0.5** - Moderate (recommended)
- **0.7** - Strict (more false positives)

### Personal Email Providers

Update the list in `shared/pricing_config.py`:

```python
PERSONAL_EMAIL_PROVIDERS = [
    'gmail.com',
    'outlook.com', 
    'hotmail.com',
    'yahoo.com',
    'aol.com',
    'icloud.com',
    'protonmail.com',
    'mail.com'
]
```

## How It Works

### Signup Flow with Protection

1. **User submits signup form**
   - Frontend generates reCAPTCHA v3 token (invisible to user)
   - Token sent with signup request

2. **Backend validation sequence**:
   ```
   ✓ Required fields validation
   ✓ Email already registered check
   ✓ Business email validation (reject gmail, yahoo, etc.)
   ✓ reCAPTCHA verification (score >= 0.5)
   ✓ Rate limit check (IP and domain)
   ✓ Domain trial eligibility check
   → Create user and trial subscription
   ```

3. **Recording**:
   - All attempts (success or failure) are logged to `signup_attempts` table
   - Old attempts (>7 days) automatically cleaned up

### Domain Trial Eligibility Rules

A domain is **eligible** for a trial if:
- No organization exists for this domain, OR
- Organization exists but has no active subscription, OR
- Previous trial ended 90+ days ago

A domain is **NOT eligible** if:
- Domain already has an active trial
- Domain has an active paid subscription
- Previous trial ended less than 90 days ago

## Error Messages for Users

### Business Email Rejected
```
"Only business email addresses are accepted. Please use your company email address to register."
```

### reCAPTCHA Failed
```
"Security verification failed. Please refresh the page and try again."
```

### Rate Limit Exceeded (IP)
```
"Too many signup attempts from your location. Please try again in 60 minutes."
```

### Rate Limit Exceeded (Domain)
```
"Multiple signup attempts detected from your organization. Please contact support if you need assistance."
```

### Domain Already Has Trial
```
"Your organization (Company Name) already has an active trial. Please contact your account administrator to add you as a user."
```

### Domain Has Paid Subscription
```
"Your organization (Company Name) already has an active subscription. Please contact your account administrator to add you as a user."
```

### Recent Trial
```
"Your organization's trial ended recently. Please contact sales@veritaslogic.ai to discuss subscription options."
```

## Monitoring & Analytics

### Check Signup Attempts

```sql
-- Recent signup attempts
SELECT * FROM signup_attempts 
ORDER BY attempted_at DESC 
LIMIT 100;

-- Failed attempts by reason
SELECT failure_reason, COUNT(*) as count
FROM signup_attempts
WHERE success = false
GROUP BY failure_reason
ORDER BY count DESC;

-- IP addresses with multiple failed attempts
SELECT ip_address, COUNT(*) as attempts
FROM signup_attempts
WHERE success = false
GROUP BY ip_address
HAVING COUNT(*) >= 3
ORDER BY attempts DESC;

-- Domains with multiple signup attempts
SELECT email_domain, 
       COUNT(*) as total_attempts,
       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
FROM signup_attempts
GROUP BY email_domain
HAVING COUNT(*) >= 2
ORDER BY total_attempts DESC;
```

### Dashboard Metrics

Track these KPIs:
- Total signup attempts (successful vs. failed)
- reCAPTCHA block rate
- Rate limit trigger rate
- Domain trial eligibility rejections
- Business email rejection rate

## Testing

### Development Testing (without reCAPTCHA)

If `RECAPTCHA_SECRET_KEY` is not set, the system automatically allows signups (development mode).

### Testing with reCAPTCHA

1. Set environment variables
2. Test with valid business email
3. Test with personal email (should be rejected)
4. Test multiple signups from same IP (should hit rate limit)
5. Test multiple signups from same domain (should check trial eligibility)

## Production Deployment

### Pre-deployment Checklist

- [ ] reCAPTCHA v3 keys configured in production environment
- [ ] `signup_attempts` table exists in production database
- [ ] Business email validation list reviewed and updated
- [ ] Rate limit thresholds reviewed for production traffic
- [ ] Error messages reviewed for clarity and professionalism
- [ ] Monitoring queries set up in database dashboard

### Post-deployment Monitoring

Monitor for first 72 hours:
- False positive rate (legitimate users blocked)
- False negative rate (abusers getting through)
- reCAPTCHA score distribution
- Rate limit trigger frequency

Adjust thresholds as needed based on real data.

## Troubleshooting

### Issue: Legitimate users blocked by reCAPTCHA

**Solution**: Lower the score threshold from 0.5 to 0.3 in `shared/trial_protection.py`

### Issue: Too many false positives on business email validation

**Solution**: Add specific domains to `APPROVED_BUSINESS_DOMAINS` in `shared/pricing_config.py`

### Issue: Rate limits too strict

**Solution**: Increase `MAX_SIGNUP_ATTEMPTS_PER_IP` or `MAX_SIGNUP_ATTEMPTS_PER_DOMAIN`

### Issue: reCAPTCHA not loading on frontend

**Solution**: 
1. Check browser console for errors
2. Verify `RECAPTCHA_SITE_KEY` is set correctly
3. Ensure domain is registered in Google reCAPTCHA admin

## Support

For issues or questions:
- **Technical**: support@veritaslogic.ai
- **reCAPTCHA**: https://developers.google.com/recaptcha/docs/v3
