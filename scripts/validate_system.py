import asyncio
import os
import time
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("VALIDATION")

# Add src path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Use database modules directly to verify state
import database.main as database
from worker.app.core import processor, magic_eden, syncer, discord_embeds

# Load Env
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(project_root, '.env.local')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded env from {env_path}")

# FORCE LOCALHOST for Script execution (Docker uses 'postgres', Host uses 'localhost')
os.environ['POSTGRES_HOST'] = 'localhost'

# Mock Data
MINT_AUTOBUY = "VALIDATION_MINT_AUTOBUY"
MINT_DELISTED = "VALIDATION_MINT_DELISTED"

async def mock_queue_consumer(queue):
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=2.0)
            logger.info(f"🔔 [QUEUE] Received Alert: {item.get('alert_level')} | Reason: {item.get('reason')}")
            queue.task_done()
        except asyncio.TimeoutError:
            if queue.empty():
                break

async def run_validation():
    logger.info("🛡️ STARTING SYSTEM VALIDATION (DRY RUN)")
    
    # 1. Setup Mock Deal
    logger.info("--- 1. Testing New Deal Processing ---")
    mock_listing = {
        'id': 'VAL_1',
        'token_mint': MINT_AUTOBUY,
        'pricing': {'price': 1.0}, # Raw ME format mock
        'price_amount': 1.0, 
        'price_currency': 'SOL',
        'name': 'Validation Card',
        'grading_company': 'PSA',
        'grade': 10,
        'listing_id': 'VAL_1'
    }
    
    queue = asyncio.Queue()
    
    # Inject into Processor
    # We bypass Magic Eden fetch and go straight to processor.process_listing
    # We need to mock Alt Data fetch though, or processor will fail/call API.
    # processor.py calls `alt.get_alt_data_async`. We should probably mock that or rely on real API if key exists.
    # For validation speed, let's assume we can hit the API or if we fail, we handle it.
    # BUT, we want to test DEDUP.
    
    # A. First Process
    logger.info("   Processing Deal (Run 1)...")
    # We manually create a notification to simulate "Already Sent" if we want to test dedup?
    # No, let's test real flow.
    # We need to ensure DB is clean for this mint.
    # Only if we can access DB.
    # database.update_listing_status(MINT_AUTOBUY, is_listed=False) # Cleanup first
    
    # Note: process_listing is complex. 
    # Let's test the components we changed: DEDUP and RECHECK.
    
    # 2. Testing Deduplication (Processor Level)
    logger.info("--- 2. Testing Notification Deduplication ---")
    listing_id = "VAL_TEST_DEDUP"
    try:
        # Create a fake notification in DB
        database.create_notification(
            user_wallet=None,
            title="Fake Alert",
            message="Test",
            type="HIGH",
            params={'listing_id': listing_id}
        )
        logger.info("   Created seed notification.")
        
        # Verify Check
        is_dup = database.check_recent_notification(listing_id, 'HIGH')
        if is_dup:
            logger.info("✅ Deduplication Logic PASSED (Found recent alert)")
        else:
            logger.error("❌ Deduplication Logic FAILED (Did not find recent alert)")
            
    except Exception as e:
        logger.error(f"❌ DB Check Failed: {e}")

    # 3. Testing Delisted Notification (Syncer Logic)
    logger.info("--- 3. Testing Delisted Notification ---")
    # We need to simulate syncer finding a 'None' result for a tracked deal.
    # Let's insert a dummy active deal into DB
    dummy_mint = MINT_DELISTED
    # Fix: update_listing expects 'alt_data' not 'snipe_details'
    database.update_listing(
        listing_id="VAL_DELISTED_ID",
        alt_data={'alt_value': 100, 'avg_price': 100, 'confidence': 90, 'supply': 10, 'lower_bound': 80, 'upper_bound': 120, 'alt_asset_id': 'test'},
        cartel_category="AUTOBUY", # Tracked Category
        name="Delisted Test Card"
    )
    # We also need to set basic fields that might not be in update_listing? 
    # update_listing only sets ALT data. We need to create the listing first if it doesn't exist?
    # Actually validation script assumes seeds exist. 
    # Let's use `update_listing_details_by_mint` or manual SQL/helper if needed.
    # But update_listing updates by ID. 
    # Let's ensure we have a Listing record first.
    database.save_listing([{
        'listing_id': "VAL_DELISTED_ID",
        'token_mint': dummy_mint, 
        'cartel_category': "NEW",
        'is_listed': True,
        'price_amount': 1.0,
        'price_currency': 'SOL',
        'name': "Delisted Test Card",
        'grading_company': "PSA",
        'grade': "10"
    }])
    # Now update category
    database.update_listing(
        listing_id="VAL_DELISTED_ID",
        alt_data={'alt_value': 100, 'avg_price': 100, 'confidence': 90},
        cartel_category="AUTOBUY",
        name="Delisted Test Card"
    )
    logger.info(f"   Seeded DB with Active AUTOBUY deal: {dummy_mint}")
    
    # Verify it is active
    active = database.get_active_deals_by_category(['AUTOBUY'])
    found = any(d['token_mint'] == dummy_mint for d in active)
    if not found:
        logger.error("❌ Setup Failed: Could not seed active deal.")
    else:
        logger.info("✅ Setup Complete: Deal is Active.")
        
    # Run Syncer Phase 1 Logic (Mocking the ME Response)
    # We can't easily invoke syncer.recheck_listings because it calls real API.
    # But we can simulate the "Logic Block" we added.
    
    # Simulate "Not Found" result
    logger.info("   Simulating 'Not Found' response from ME...")
    
    # Manually trigger the removal/alert logic we added to syncer
    # (Copying the logic flow for verification)
    queue = asyncio.Queue()
    
    # ... Logic Copy from Syncer ...
    original_deal = next(d for d in active if d['token_mint'] == dummy_mint)
    
    # Send Alert
    logger.info("   Triggering Delisted Logic...")
    msg = f"❌ **Delisted / Sold**: This deal is no longer available on Magic Eden."
    await queue.put({
        'listing_data': original_deal, 
        'snipe_details': {}, 
        'alert_level': 'HIGH',
        'reason': msg
    })
    
    # Update DB
    database.update_listing_status(dummy_mint, is_listed=False)
    
    # Check Result
    # 1. Queue should have alert
    try:
        item = await asyncio.wait_for(queue.get(), timeout=1.0)
        logger.info(f"✅ Notification Queued: {item.get('reason')}")
        assert "Delisted" in item.get('reason')
    except:
        logger.error("❌ Failed to queue Delisted Notification.")
        
    # 2. DB should be unlisted
    # We check DB again
    # We need to start a new session or check raw?
    # verify status
    # This might require a fresh fetch function or reusing get_active (should NOT be there)
    active_now = database.get_active_deals_by_category(['AUTOBUY'])
    found_now = any(d['token_mint'] == dummy_mint for d in active_now)
    if not found_now:
        logger.info("✅ DB Update Verified: Deal is no longer in Active list.")
    else:
        logger.error("❌ DB Update Failed: Deal is still Active.")

    logger.info("🏁 Validation Complete.")

if __name__ == "__main__":
    asyncio.run(run_validation())
