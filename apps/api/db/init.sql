-- AI Stock Assistant Database Schema
-- PostgreSQL 16

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create portfolios table
CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'Main Portfolio',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create holdings table
CREATE TABLE IF NOT EXISTS holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    shares DECIMAL(18, 6) NOT NULL CHECK (shares > 0),
    avg_cost DECIMAL(18, 4) NOT NULL CHECK (avg_cost >= 0),
    acquired_at DATE,
    sector TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_portfolio_symbol UNIQUE (portfolio_id, symbol)
);

-- Create watchlists table
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    target_price_low DECIMAL(18, 4),
    target_price_high DECIMAL(18, 4),
    notes TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_symbol_watchlist UNIQUE(user_id, symbol)
);

ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS target_price_low DECIMAL(18, 4);
ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS target_price_high DECIMAL(18, 4);

-- Create alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    condition_type TEXT NOT NULL CHECK (condition_type IN ('price_above', 'price_below', 'percent_change', 'volume_spike', 'insider_buy', 'earnings_soon')),
    threshold JSONB NOT NULL,
    message TEXT,
    triggered_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id TEXT NOT NULL,
    message_role TEXT NOT NULL CHECK (message_role IN ('user', 'assistant')),
    message_content TEXT NOT NULL,
    agent_used TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('buy', 'sell', 'dividend')),
    shares DECIMAL(18, 6) NOT NULL CHECK (shares > 0),
    price DECIMAL(18, 4) NOT NULL CHECK (price >= 0),
    fees DECIMAL(18, 4) NOT NULL DEFAULT 0,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    report JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_prompt_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_key TEXT NOT NULL,
    report_type TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_owner_report_prompt UNIQUE (owner_key, report_type)
);

CREATE TABLE IF NOT EXISTS report_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_key TEXT NOT NULL,
    report_type TEXT NOT NULL,
    base_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    effective_prompt TEXT NOT NULL,
    latest_report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_thread_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES report_threads(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS broker_api_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    app_type TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INT,
    attempt INT NOT NULL DEFAULT 1,
    latency_ms INT,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT,
    request_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trade_hitl_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL DEFAULT 'schwab',
    account_number TEXT,
    action TEXT NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    reviewer TEXT,
    ticket_id TEXT,
    reason TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlists(symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active, user_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts(symbol) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON transactions(portfolio_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_runs_type ON report_runs(report_type, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_prompt_overrides_owner ON report_prompt_overrides(owner_key, report_type);
CREATE INDEX IF NOT EXISTS idx_report_threads_owner_updated ON report_threads(owner_key, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_thread_messages_thread_created ON report_thread_messages(thread_id, created_at ASC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_holdings_updated_at BEFORE UPDATE ON holdings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_report_prompt_overrides_updated_at BEFORE UPDATE ON report_prompt_overrides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_report_threads_updated_at BEFORE UPDATE ON report_threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default test user (for development)
INSERT INTO users (username, email) VALUES ('testuser', 'test@example.com')
ON CONFLICT (username) DO NOTHING;

-- Get the user ID and create default portfolio
DO $$
DECLARE
    user_uuid UUID;
BEGIN
    SELECT id INTO user_uuid FROM users WHERE username = 'testuser';

    IF user_uuid IS NOT NULL THEN
        INSERT INTO portfolios (user_id, name, description)
        VALUES (user_uuid, 'Main Portfolio', 'Default portfolio for testing')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

COMMENT ON TABLE users IS 'Application users';
COMMENT ON TABLE portfolios IS 'User investment portfolios';
COMMENT ON TABLE holdings IS 'Individual stock positions within portfolios';
COMMENT ON TABLE watchlists IS 'Stocks users are watching';
COMMENT ON TABLE alerts IS 'Price and event alerts configured by users';
COMMENT ON TABLE conversations IS 'Chat history for memory and context';
COMMENT ON TABLE report_prompt_overrides IS 'Per-owner editable prompt templates for institutional report workflows';
COMMENT ON TABLE report_threads IS 'Persisted report threads for threaded follow-up Q&A';
COMMENT ON TABLE report_thread_messages IS 'Conversation messages within a report thread';
