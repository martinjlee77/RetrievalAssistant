-- ==========================================
-- RAILWAY PRODUCTION MIGRATION SCRIPT
-- Subscription System Migration
-- ==========================================
-- This script migrates from credit-based to subscription-based system
-- Safe for production: Uses IF NOT EXISTS and ALTER TABLE ADD IF NOT EXISTS
-- ==========================================

-- ==========================================
-- STEP 1: CREATE NEW TABLES
-- ==========================================

-- Organizations table (new)
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    domain VARCHAR(255),
    stripe_customer_id VARCHAR(255) UNIQUE,
    azure_tenant_id VARCHAR(255),
    region_preference VARCHAR(50) DEFAULT 'US',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Subscription Plans table (new)
CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_key VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    price_monthly DECIMAL(10,2) NOT NULL,
    word_allowance INTEGER NOT NULL,
    seats INTEGER DEFAULT 1,
    features JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    stripe_product_id TEXT,
    stripe_price_id TEXT NOT NULL
);

-- Subscription Instances table (new)
CREATE TABLE IF NOT EXISTS subscription_instances (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) NOT NULL,
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Subscription Usage table (new)
CREATE TABLE IF NOT EXISTS subscription_usage (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES subscription_instances(id) ON DELETE CASCADE,
    month_start DATE NOT NULL,
    month_end DATE NOT NULL,
    word_allowance INTEGER NOT NULL,
    words_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(subscription_id, month_start)
);

-- Rollover Ledger table (new)
CREATE TABLE IF NOT EXISTS rollover_ledger (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES subscription_instances(id) ON DELETE CASCADE,
    grant_month DATE NOT NULL,
    amount_granted INTEGER NOT NULL,
    amount_remaining INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Stripe Webhook Events table (new)
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Lead Sources table (new)
CREATE TABLE IF NOT EXISTS lead_sources (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,
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
-- STEP 2: MODIFY EXISTING USERS TABLE
-- ==========================================

-- Add new columns to users table (safe: IF NOT EXISTS)
DO $$
BEGIN
    -- Add org_id column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='org_id') THEN
        ALTER TABLE users ADD COLUMN org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE;
    END IF;
    
    -- Add role column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='role') THEN
        ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'member';
    END IF;
    
    -- Add job_title column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='job_title') THEN
        ALTER TABLE users ADD COLUMN job_title VARCHAR(100);
    END IF;
    
    -- Add research_assistant_access column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='research_assistant_access') THEN
        ALTER TABLE users ADD COLUMN research_assistant_access BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add marketing_opt_in column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='marketing_opt_in') THEN
        ALTER TABLE users ADD COLUMN marketing_opt_in BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add preferences column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='preferences') THEN
        ALTER TABLE users ADD COLUMN preferences JSONB DEFAULT '{}';
    END IF;
    
    -- Add last_login_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='last_login_at') THEN
        ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;
    END IF;
END $$;

-- ==========================================
-- STEP 3: MODIFY EXISTING ANALYSES TABLE
-- ==========================================

DO $$
BEGIN
    -- Add org_id column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='analyses' AND column_name='org_id') THEN
        ALTER TABLE analyses ADD COLUMN org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE;
    END IF;
    
    -- Add words_charged column (actual words deducted from allowance)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='analyses' AND column_name='words_charged') THEN
        ALTER TABLE analyses ADD COLUMN words_charged INTEGER;
    END IF;
    
    -- Ensure error_message column exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='analyses' AND column_name='error_message') THEN
        ALTER TABLE analyses ADD COLUMN error_message TEXT;
    END IF;
END $$;

-- ==========================================
-- STEP 4: CREATE INDEXES
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);
CREATE INDEX IF NOT EXISTS idx_organizations_stripe_customer_id ON organizations(stripe_customer_id);

CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);

CREATE INDEX IF NOT EXISTS idx_subscription_instances_org_id ON subscription_instances(org_id);
CREATE INDEX IF NOT EXISTS idx_subscription_instances_stripe_id ON subscription_instances(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_instances_status ON subscription_instances(status);

CREATE INDEX IF NOT EXISTS idx_subscription_usage_org_id ON subscription_usage(org_id);
CREATE INDEX IF NOT EXISTS idx_subscription_usage_subscription_id ON subscription_usage(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_usage_month_start ON subscription_usage(month_start);

CREATE INDEX IF NOT EXISTS idx_rollover_ledger_org_id ON rollover_ledger(org_id);
CREATE INDEX IF NOT EXISTS idx_rollover_ledger_expires_at ON rollover_ledger(expires_at);

CREATE INDEX IF NOT EXISTS idx_analyses_org_id ON analyses(org_id);

CREATE INDEX IF NOT EXISTS idx_lead_sources_user_id ON lead_sources(user_id);
CREATE INDEX IF NOT EXISTS idx_lead_sources_source ON lead_sources(source);

CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_event_id ON stripe_webhook_events(event_id);

-- Partial unique index: only ONE active/trial/past_due subscription per org
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_subscription_per_org 
ON subscription_instances(org_id) 
WHERE status IN ('active', 'trial', 'past_due');

-- ==========================================
-- STEP 5: SEED SUBSCRIPTION PLANS
-- ==========================================

INSERT INTO subscription_plans (plan_key, name, price_monthly, word_allowance, seats, features, stripe_price_id)
VALUES 
    ('professional', 'Professional', 295.00, 30000, 1, 
     '["All ASC standards", "Research Assistant", "DOCX/PDF output", "Priority support"]',
     'price_professional_placeholder'),
    ('team', 'Team', 595.00, 75000, 3, 
     '["All ASC standards", "Research Assistant", "DOCX/PDF output", "Priority support", "Multi-user organization", "Audit logs"]',
     'price_team_placeholder'),
    ('enterprise', 'Enterprise', 1195.00, 180000, 999, 
     '["All ASC standards", "Research Assistant", "DOCX/PDF output", "Dedicated success manager", "Custom SLA", "Azure OpenAI option", "Unlimited internal viewers"]',
     'price_enterprise_placeholder')
ON CONFLICT (plan_key) DO UPDATE SET
    price_monthly = EXCLUDED.price_monthly,
    word_allowance = EXCLUDED.word_allowance,
    seats = EXCLUDED.seats,
    features = EXCLUDED.features;

-- ==========================================
-- MIGRATION COMPLETE
-- ==========================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'VeritasLogic Subscription Migration Complete!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'New tables created:';
    RAISE NOTICE '  - organizations';
    RAISE NOTICE '  - subscription_plans (3 plans seeded)';
    RAISE NOTICE '  - subscription_instances';
    RAISE NOTICE '  - subscription_usage';
    RAISE NOTICE '  - rollover_ledger';
    RAISE NOTICE '  - stripe_webhook_events';
    RAISE NOTICE '  - lead_sources';
    RAISE NOTICE '';
    RAISE NOTICE 'Existing tables updated:';
    RAISE NOTICE '  - users (added org_id, role, job_title, etc.)';
    RAISE NOTICE '  - analyses (added org_id, words_charged)';
    RAISE NOTICE '';
    RAISE NOTICE 'Plans: Professional ($295/30K), Team ($595/75K), Enterprise ($1195/180K)';
    RAISE NOTICE '';
    RAISE NOTICE 'IMPORTANT: Update Stripe price IDs in subscription_plans table';
    RAISE NOTICE '==============================================';
END $$;
