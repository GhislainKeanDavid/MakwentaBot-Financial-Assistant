-- Migration: Create recurring_expenses table
-- Execute this in Supabase SQL Editor before deploying code changes

CREATE TABLE IF NOT EXISTS recurring_expenses (
    recurring_id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    frequency TEXT NOT NULL CHECK (frequency IN ('daily', 'weekly', 'biweekly', 'monthly', 'yearly')),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    next_occurrence DATE NOT NULL,
    last_processed DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_end_date CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_recurring_user_active
    ON recurring_expenses(user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_recurring_next_occurrence
    ON recurring_expenses(next_occurrence, is_active);

-- Comments for documentation
COMMENT ON TABLE recurring_expenses IS 'Stores recurring expenses that auto-generate transactions';
COMMENT ON COLUMN recurring_expenses.next_occurrence IS 'The next date this expense should be recorded';
COMMENT ON COLUMN recurring_expenses.last_processed IS 'The last date a transaction was auto-created';
COMMENT ON COLUMN recurring_expenses.is_active IS 'Whether this recurring expense is currently active (false = paused)';
