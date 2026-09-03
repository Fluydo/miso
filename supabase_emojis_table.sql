-- Create emojis table for Discord emoji sync
CREATE TABLE IF NOT EXISTS emojis (
    guild_id TEXT NOT NULL,
    emoji_id TEXT NOT NULL,
    emoji_name TEXT NOT NULL,
    emoji_animated BOOLEAN DEFAULT FALSE,
    emoji_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (guild_id, emoji_id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_emojis_guild_id ON emojis(guild_id);

-- Enable Row Level Security
ALTER TABLE emojis ENABLE ROW LEVEL SECURITY;

-- Policy: Allow anonymous read access (for web dashboard)
CREATE POLICY "Allow anonymous read access to emojis"
    ON emojis
    FOR SELECT
    TO anon
    USING (true);

-- Policy: Allow service role full access
CREATE POLICY "Allow service role full access to emojis"
    ON emojis
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
