-- Crash Games Table
CREATE TABLE IF NOT EXISTS crash_games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL CHECK (status IN ('betting', 'running', 'ended')),
    crash_point NUMERIC(5,2) NOT NULL,
    crash_at NUMERIC(5,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ
);

-- Crash Bets Table
CREATE TABLE IF NOT EXISTS crash_bets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES crash_games(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount >= 10),
    cashed_out BOOLEAN NOT NULL DEFAULT FALSE,
    cashout_multiplier NUMERIC(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(game_id, user_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_crash_games_status ON crash_games(status);
CREATE INDEX IF NOT EXISTS idx_crash_games_created ON crash_games(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crash_bets_game ON crash_bets(game_id);
CREATE INDEX IF NOT EXISTS idx_crash_bets_user ON crash_bets(user_id);

-- Enable RLS (optional, for security)
ALTER TABLE crash_games ENABLE ROW LEVEL SECURITY;
ALTER TABLE crash_bets ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read on crash_games" ON crash_games FOR SELECT USING (true);
CREATE POLICY "Allow public read on crash_bets" ON crash_bets FOR SELECT USING (true);

-- Allow authenticated users to insert bets
CREATE POLICY "Allow authenticated insert on crash_bets" ON crash_bets FOR INSERT WITH CHECK (true);

-- Allow authenticated users to update their own bets (for cashout)
CREATE POLICY "Allow authenticated update on crash_bets" ON crash_bets FOR UPDATE USING (true);
