-- Add blacklisted_keywords column to user_settings
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS blacklisted_keywords TEXT DEFAULT 'black star,sticker,stickers';
