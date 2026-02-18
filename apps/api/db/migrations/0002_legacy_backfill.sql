-- Backfill legacy schema drift from earlier local databases.

ALTER TABLE holdings ADD COLUMN IF NOT EXISTS sector TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS target_price_low DECIMAL(18, 4);
ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS target_price_high DECIMAL(18, 4);

DO $$
BEGIN
    IF to_regclass('public.watchlist') IS NOT NULL THEN
        INSERT INTO watchlists (id, user_id, symbol, target_price_low, target_price_high, notes, added_at)
        SELECT
            COALESCE(w.id, gen_random_uuid()),
            w.user_id,
            UPPER(w.symbol),
            w.target_price_low,
            w.target_price_high,
            w.notes,
            COALESCE(w.added_at, NOW())
        FROM watchlist w
        ON CONFLICT (user_id, symbol) DO UPDATE
        SET
            target_price_low = COALESCE(EXCLUDED.target_price_low, watchlists.target_price_low),
            target_price_high = COALESCE(EXCLUDED.target_price_high, watchlists.target_price_high),
            notes = COALESCE(EXCLUDED.notes, watchlists.notes);
    END IF;
END $$;
