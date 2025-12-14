-- Migration to add priority column to user_settings
-- Created: 2025-12-14
-- Purpose: Support multi-user priority execution ("Shotgun" strategy)

DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='user_settings' AND column_name='priority') THEN
        ALTER TABLE user_settings ADD COLUMN priority INTEGER DEFAULT 10;
    END IF;
END $$;
