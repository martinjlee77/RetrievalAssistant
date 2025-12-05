-- VeritasLogic Subscription-Based Database Schema
-- Fresh start optimized for word-allowance subscriptions
-- Run this to replace the old credit-based system

-- ==========================================
-- ORGANIZATIONS
-- ==========================================
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    domain VARCHAR(255),  -- Email domain for auto-org assignment
    stripe_customer_id VARCHAR(255) UNIQUE,
    azure_tenant_id VARCHAR(255),  -- For future Azure AD integration
    region_preference VARCHAR(50) DEFAULT 'US',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- SUBSCRIPTION PLANS (catalog)
-- ==========================================
CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_key VARCHAR(50) UNIQUE NOT NULL,  -- 'professional', 'team', 'enterprise'
    name VARCHAR(100) NOT NULL,
    price_monthly DECIMAL(10,2) NOT NULL,
    word_allowance INTEGER NOT NULL,  -- Monthly word limit
    seats INTEGER DEFAULT 1,  -- Number of users allowed
    features JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- USERS (updated for organizations)
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    job_title VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',  -- 'owner', 'admin', 'member'
    email_verified BOOLEAN DEFAULT FALSE,
    research_assistant_access BOOLEAN DEFAULT FALSE,
    marketing_opt_in BOOLEAN DEFAULT FALSE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

-- ==========================================
-- SUBSCRIPTION INSTANCES (active subscriptions)
-- ==========================================
CREATE TABLE IF NOT EXISTS subscription_instances (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) NOT NULL,  -- 'trial', 'active', 'past_due', 'canceled', 'expired'
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- SUBSCRIPTION USAGE (monthly word tracking)
-- ==========================================
CREATE TABLE IF NOT EXISTS subscription_usage (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES subscription_instances(id) ON DELETE CASCADE,
    month_start DATE NOT NULL,  -- First day of billing month
    month_end DATE NOT NULL,    -- Last day of billing month
    word_allowance INTEGER NOT NULL,  -- Base monthly allowance from plan
    words_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    -- UNIQUE per subscription (not org) to allow trial->paid transition
    UNIQUE(subscription_id, month_start)
);

-- ==========================================
-- ROLLOVER LEDGER (12-month rollover tracking)
-- ==========================================
CREATE TABLE IF NOT EXISTS rollover_ledger (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES subscription_instances(id) ON DELETE CASCADE,
    grant_month DATE NOT NULL,  -- Month when words were originally granted
    amount_granted INTEGER NOT NULL,  -- Original unused words from that month
    amount_remaining INTEGER NOT NULL,  -- How many still available
    expires_at TIMESTAMP NOT NULL,  -- 12 months from grant_month
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- ANALYSES (updated to track words used)
-- ==========================================
CREATE TABLE IF NOT EXISTS analyses (
    analysis_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    asc_standard VARCHAR(50) NOT NULL,
    words_count INTEGER,
    tier_name VARCHAR(50),
    words_charged INTEGER,  -- Actual words deducted from allowance
    status VARCHAR(50),
    memo_uuid VARCHAR(255),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    file_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- LEAD SOURCES (AppSource attribution)
-- ==========================================
CREATE TABLE IF NOT EXISTS lead_sources (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,  -- 'appsource', 'website', 'referral', etc.
    campaign VARCHAR(100),
    medium VARCHAR(100),
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    utm_content VARCHAR(255),
    utm_term VARCHAR(255),
    referrer VARCHAR(500),
    landing_page VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- EMAIL VERIFICATION TOKENS (kept from old schema)
-- ==========================================
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- PASSWORD RESET TOKENS (kept from old schema)
-- ==========================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- SUPPORT TICKETS (kept from old schema)
-- ==========================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'normal',
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- STRIPE WEBHOOK EVENTS (for idempotency)
-- ==========================================
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- INDEXES FOR PERFORMANCE
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);
CREATE INDEX IF NOT EXISTS idx_organizations_stripe_customer_id ON organizations(stripe_customer_id);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);

CREATE INDEX IF NOT EXISTS idx_subscription_instances_org_id ON subscription_instances(org_id);
CREATE INDEX IF NOT EXISTS idx_subscription_instances_stripe_id ON subscription_instances(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_instances_status ON subscription_instances(status);

CREATE INDEX IF NOT EXISTS idx_subscription_usage_org_id ON subscription_usage(org_id);
CREATE INDEX IF NOT EXISTS idx_subscription_usage_subscription_id ON subscription_usage(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_usage_month_start ON subscription_usage(month_start);

CREATE INDEX IF NOT EXISTS idx_rollover_ledger_org_id ON rollover_ledger(org_id);
CREATE INDEX IF NOT EXISTS idx_rollover_ledger_expires_at ON rollover_ledger(expires_at);

-- Partial unique index: only ONE active/trial/past_due subscription per org
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_subscription_per_org 
ON subscription_instances(org_id) 
WHERE status IN ('active', 'trial', 'past_due');

CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_org_id ON analyses(org_id);
CREATE INDEX IF NOT EXISTS idx_analyses_memo_uuid ON analyses(memo_uuid);
CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);

CREATE INDEX IF NOT EXISTS idx_lead_sources_user_id ON lead_sources(user_id);
CREATE INDEX IF NOT EXISTS idx_lead_sources_source ON lead_sources(source);

CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_event_id ON stripe_webhook_events(event_id);

-- ==========================================
-- INSERT DEFAULT SUBSCRIPTION PLANS
-- ==========================================
INSERT INTO subscription_plans (plan_key, name, price_monthly, word_allowance, seats, features)
VALUES 
    ('professional', 'Professional', 295.00, 150000, 1, '["All ASC standards", "Research Assistant", "DOCX/PDF output", "Priority support", "12-month word rollover"]'),
    ('team', 'Team', 595.00, 400000, 1, '["All ASC standards", "Research Assistant", "DOCX/PDF output", "Priority support", "12-month word rollover"]'),
    ('enterprise', 'Enterprise', 1195.00, 1000000, 1, '["All ASC standards", "Research Assistant", "DOCX/PDF output", "Dedicated success manager", "Custom SLA", "12-month word rollover"]')
ON CONFLICT (plan_key) DO UPDATE SET
    price_monthly = EXCLUDED.price_monthly,
    word_allowance = EXCLUDED.word_allowance,
    seats = EXCLUDED.seats,
    features = EXCLUDED.features;

-- ==========================================
-- SUCCESS MESSAGE
-- ==========================================
DO $$
BEGIN
    RAISE NOTICE 'VeritasLogic subscription database schema created successfully!';
    RAISE NOTICE 'Tables created: organizations, subscription_plans, subscription_instances, subscription_usage, users, analyses, lead_sources';
    RAISE NOTICE 'Default plans: Professional ($295/150K), Team ($595/400K), Enterprise ($1195/1M)';
END $$;
