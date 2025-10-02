-- VeritasLogic Railway PostgreSQL Database Setup Script
-- Run this script once on your new Railway PostgreSQL database to create all required tables

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    job_title VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    terms_accepted_at TIMESTAMP DEFAULT NOW(),
    email_verified BOOLEAN DEFAULT FALSE,
    credits_balance DECIMAL(10,2) DEFAULT 0.00,
    marketing_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    preferences JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create email verification tokens table
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create analyses table
CREATE TABLE IF NOT EXISTS analyses (
    analysis_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asc_standard VARCHAR(50) NOT NULL,
    words_count INTEGER,
    est_api_cost DECIMAL(10,4),
    final_charged_credits DECIMAL(10,2),
    billed_credits DECIMAL(10,2),
    tier_name VARCHAR(50),
    status VARCHAR(50),
    memo_uuid VARCHAR(255),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    file_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create credit transactions table
CREATE TABLE IF NOT EXISTS credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_id INTEGER REFERENCES analyses(analysis_id) ON DELETE SET NULL,
    amount DECIMAL(10,2) NOT NULL,
    reason VARCHAR(100) NOT NULL,
    balance_after DECIMAL(10,2),
    memo_uuid VARCHAR(255),
    metadata JSONB,
    expires_at TIMESTAMP,
    stripe_payment_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user_id ON email_verification_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_token ON email_verification_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_memo_uuid ON analyses(memo_uuid);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_analysis_id ON credit_transactions(analysis_id);

-- Insert a test admin user (optional - you can remove this if you don't want it)
-- Password is 'test123' - CHANGE THIS IMMEDIATELY
INSERT INTO users (email, first_name, last_name, company_name, job_title, password_hash, email_verified, credits_balance)
VALUES (
    'admin@veritaslogic.ai',
    'Admin',
    'User',
    'VeritasLogic',
    'Administrator',
    '$2b$12$ZC5K8HJf9QRJ7yU9VQz9.ewcvTGJpR1jYf8QQx8rJmK9iRrJ8r9m6', -- 'test123' hashed
    TRUE,
    1000.00
) ON CONFLICT (email) DO NOTHING;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'VeritasLogic database tables created successfully!';
    RAISE NOTICE 'Tables created: users, email_verification_tokens, password_reset_tokens, analyses, credit_transactions';
    RAISE NOTICE 'Test admin user: admin@veritaslogic.ai (password: test123 - CHANGE THIS!)';
END $$;