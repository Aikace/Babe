-- ══════════════════════════════════════════════════════
--  Babe Sniper — Supabase Setup SQL
--  Run this once in your Supabase SQL Editor
-- ══════════════════════════════════════════════════════

-- ── watchlist ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlist (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  username      text        NOT NULL,
  platform      text        NOT NULL CHECK (platform IN ('instagram','x','both')),
  priority      text        NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('HIGH','MEDIUM','LOW')),
  value_score   integer     NOT NULL DEFAULT 0,
  value_estimate text,
  status        text        NOT NULL DEFAULT 'monitoring'
                            CHECK (status IN ('monitoring','available','claimed')),
  last_checked  timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (username, platform)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_status   ON watchlist (status);
CREATE INDEX IF NOT EXISTS idx_watchlist_priority ON watchlist (priority);
CREATE INDEX IF NOT EXISTS idx_watchlist_score    ON watchlist (value_score DESC);

-- ── claimed ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS claimed (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  username      text        NOT NULL,
  platform      text        NOT NULL,
  value_score   integer     DEFAULT 0,
  value_estimate text,
  account_used  text,
  claimed_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_claimed_score ON claimed (value_score DESC);

-- ── Row Level Security (allow service_role full access) ─
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE claimed   ENABLE ROW LEVEL SECURITY;

-- Allow anon reads for the dashboard
CREATE POLICY "Public read watchlist" ON watchlist FOR SELECT USING (true);
CREATE POLICY "Public read claimed"   ON claimed   FOR SELECT USING (true);

-- Service role handles all writes (bypasses RLS automatically)

SELECT 'Setup complete! Watchlist and claimed tables are ready.' AS status;
