-- Add min_price column to user_settings
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS min_price FLOAT DEFAULT 0.0;
