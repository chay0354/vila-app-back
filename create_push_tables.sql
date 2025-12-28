-- Create push_tokens table to store device tokens for push notifications
CREATE TABLE IF NOT EXISTS push_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    token TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('android', 'ios', 'web')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(username, platform)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_push_tokens_username ON push_tokens(username);
CREATE INDEX IF NOT EXISTS idx_push_tokens_platform ON push_tokens(platform);

-- Create push_notifications table to track sent notifications (optional, for logging)
CREATE TABLE IF NOT EXISTS push_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    username TEXT,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_count INTEGER DEFAULT 0
);

-- Create index for push_notifications
CREATE INDEX IF NOT EXISTS idx_push_notifications_username ON push_notifications(username);
CREATE INDEX IF NOT EXISTS idx_push_notifications_created_at ON push_notifications(created_at DESC);

