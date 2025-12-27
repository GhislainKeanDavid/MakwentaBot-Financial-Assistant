-- Migration 002: Create users, authentication, and chat session tables
-- This migration adds web authentication support while maintaining Telegram bot compatibility

-- Users table for web authentication
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,  -- NULL for Google OAuth users
    google_id TEXT UNIQUE,  -- NULL for email/password users
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Chat sessions for conversation management
CREATE TABLE chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat messages for persistent conversation history
CREATE TABLE chat_messages (
    message_id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('human', 'ai', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,  -- Store tool execution data
    created_at TIMESTAMP DEFAULT NOW()
);

-- Telegram migration mapping table
-- Links existing Telegram users to new web accounts
CREATE TABLE telegram_migrations (
    telegram_user_id TEXT PRIMARY KEY,
    web_user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    migrated_at TIMESTAMP DEFAULT NOW()
);

-- Add web_user_id column to existing tables for dual support
-- During migration period, records can have either user_id (Telegram) or web_user_id (web)
ALTER TABLE transactions ADD COLUMN web_user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE budgets ADD COLUMN web_user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE goals ADD COLUMN web_user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE recurring_expenses ADD COLUMN web_user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE;

-- Performance indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX idx_transactions_web_user_id ON transactions(web_user_id) WHERE web_user_id IS NOT NULL;
CREATE INDEX idx_budgets_web_user_id ON budgets(web_user_id) WHERE web_user_id IS NOT NULL;
CREATE INDEX idx_goals_web_user_id ON goals(web_user_id) WHERE web_user_id IS NOT NULL;
CREATE INDEX idx_recurring_expenses_web_user_id ON recurring_expenses(web_user_id) WHERE web_user_id IS NOT NULL;

-- Update trigger for chat_sessions updated_at
CREATE OR REPLACE FUNCTION update_chat_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions SET updated_at = NOW() WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chat_session_timestamp
AFTER INSERT ON chat_messages
FOR EACH ROW
EXECUTE FUNCTION update_chat_session_timestamp();

-- Comments for documentation
COMMENT ON TABLE users IS 'Web application users with email/password or Google OAuth authentication';
COMMENT ON TABLE chat_sessions IS 'Individual chat conversation sessions';
COMMENT ON TABLE chat_messages IS 'Persistent message history for chat sessions';
COMMENT ON TABLE telegram_migrations IS 'Mapping between Telegram user IDs and web user accounts';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password (NULL for OAuth users)';
COMMENT ON COLUMN users.google_id IS 'Google OAuth user ID (NULL for email/password users)';
