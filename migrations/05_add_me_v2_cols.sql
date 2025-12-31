ALTER TABLE listings ADD COLUMN IF NOT EXISTS auction_house VARCHAR;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS seller_referral VARCHAR;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS expiry BIGINT;  -- ME API returns expiry as large integer
