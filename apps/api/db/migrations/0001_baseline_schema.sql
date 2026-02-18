-- Baseline schema (idempotent).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'Main Portfolio',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    condition_type TEXT NOT NULL CHECK (
        condition_type IN (
            'price_above', 'price_below', 'percent_change', 'volume_spike',
            'insider_buy', 'earnings_soon', 'rsi_above', 'rsi_below', 'insider_sell'
        )
    ),
    threshold JSONB NOT NULL,
    message TEXT,
    triggered_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ
);

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

ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS name TEXT DEFAULT 'Main Portfolio';
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE holdings ADD COLUMN IF NOT EXISTS acquired_at DATE;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS sector TEXT;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS target_price_low DECIMAL(18, 4);
ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS target_price_high DECIMAL(18, 4);
ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS added_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS threshold JSONB DEFAULT '{}'::jsonb;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS triggered_at TIMESTAMPTZ;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ;

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS thread_id TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS message_role TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS message_content TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS agent_used TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS metadata JSONB;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS portfolio_id UUID;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS symbol TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS action TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS shares DECIMAL(18, 6);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS price DECIMAL(18, 4);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS fees DECIMAL(18, 4) DEFAULT 0;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS executed_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol);
CREATE UNIQUE INDEX IF NOT EXISTS ux_holdings_portfolio_symbol ON holdings(portfolio_id, symbol);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlists(symbol);
CREATE UNIQUE INDEX IF NOT EXISTS ux_watchlists_user_symbol ON watchlists(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active, user_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts(symbol) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON transactions(portfolio_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_runs_type ON report_runs(report_type, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_broker_api_events_created ON broker_api_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_hitl_audit_created ON trade_hitl_audit(created_at DESC);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_portfolios_updated_at') THEN
        CREATE TRIGGER update_portfolios_updated_at
            BEFORE UPDATE ON portfolios
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_holdings_updated_at') THEN
        CREATE TRIGGER update_holdings_updated_at
            BEFORE UPDATE ON holdings
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'name'
    ) THEN
        EXECUTE $i$
            INSERT INTO users (id, username, email, name)
            VALUES (
                '00000000-0000-0000-0000-000000000001',
                'dev_user',
                'dev-user@local',
                'Dev User'
            )
            ON CONFLICT (id) DO NOTHING
        $i$;
    ELSE
        INSERT INTO users (id, username, email)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'dev_user',
            'dev-user@local'
        )
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

INSERT INTO portfolios (id, user_id, name, description)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Main Portfolio',
    'Default portfolio for development and integration tests'
)
ON CONFLICT (id) DO NOTHING;
