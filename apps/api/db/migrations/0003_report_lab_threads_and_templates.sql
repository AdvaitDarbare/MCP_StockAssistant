-- Report Lab prompt overrides and threaded follow-up persistence.

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

CREATE INDEX IF NOT EXISTS idx_report_prompt_overrides_owner
    ON report_prompt_overrides(owner_key, report_type);
CREATE INDEX IF NOT EXISTS idx_report_threads_owner_updated
    ON report_threads(owner_key, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_thread_messages_thread_created
    ON report_thread_messages(thread_id, created_at ASC);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'update_updated_at_column'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger WHERE tgname = 'update_report_prompt_overrides_updated_at'
        ) THEN
            CREATE TRIGGER update_report_prompt_overrides_updated_at
                BEFORE UPDATE ON report_prompt_overrides
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger WHERE tgname = 'update_report_threads_updated_at'
        ) THEN
            CREATE TRIGGER update_report_threads_updated_at
                BEFORE UPDATE ON report_threads
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        END IF;
    END IF;
END $$;
