-- Migration to sync database schema to current codebase
-- Adds missing columns to user_settings table
-- Created: 2025-12-14

DO $$ 
BEGIN 
    -- 1. rpc_endpoint
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='rpc_endpoint') THEN
        ALTER TABLE user_settings ADD COLUMN rpc_endpoint VARCHAR DEFAULT 'https://api.mainnet-beta.solana.com';
    END IF;

    -- 2. jito_tip_amount
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='jito_tip_amount') THEN
        ALTER TABLE user_settings ADD COLUMN jito_tip_amount FLOAT DEFAULT 0.001;
    END IF;

    -- 3. encrypted_private_key
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='encrypted_private_key') THEN
        ALTER TABLE user_settings ADD COLUMN encrypted_private_key VARCHAR NULL;
    END IF;

    -- 4. priority (Added previously, but good to ensure)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='priority') THEN
        ALTER TABLE user_settings ADD COLUMN priority INTEGER DEFAULT 10;
    END IF;

    -- 5. Thresholds (gold_discount_percent)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='gold_discount_percent') THEN
        ALTER TABLE user_settings ADD COLUMN gold_discount_percent INTEGER DEFAULT 30;
    END IF;

    -- 6. Thresholds (red_discount_percent)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='red_discount_percent') THEN
        ALTER TABLE user_settings ADD COLUMN red_discount_percent INTEGER DEFAULT 20;
    END IF;

    -- 7. Thresholds (blue_discount_percent)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='blue_discount_percent') THEN
        ALTER TABLE user_settings ADD COLUMN blue_discount_percent INTEGER DEFAULT 10;
    END IF;

    -- 8. push_enabled
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_settings' AND column_name='push_enabled') THEN
        ALTER TABLE user_settings ADD COLUMN push_enabled BOOLEAN DEFAULT TRUE;
    END IF;

END $$;
