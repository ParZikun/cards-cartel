import time
import asyncio
import yaml
import logging
import logging.config
import database
import get_magic_eden_data as me
import get_alt_data as alt
import utils as utils
import discord_bot
from datetime import datetime

# --- Setup Logging ---
with open('logging_config.yaml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
logger = logging.getLogger(__name__)

verification_queue = asyncio.Queue()

async def reaper(queue: asyncio.Queue):
    """Pulls a mint address from the queue, verifies its status, and acts on it."""
    logger.info("--- Starting Reaper ---")
    loop = asyncio.get_running_loop()
    while True:
        try:
            mint_address = await queue.get()
            
            status = await loop.run_in_executor(
                None, me.check_listing_status, mint_address
            )

            if status == "listed":
                # If still listed, put it back at the end of the queue
                await queue.put(mint_address)
            else:
                # If 'unlisted', 'not_found', or any other error status
                logger.info(f"Reaper: Listing {mint_address} is no longer active (status: {status}). Updating DB.")
                await loop.run_in_executor(
                    None, database.update_listing_status, mint_address, False
                )
                # TODO: Add call to your Discord notification function to grey out the card.
                # e.g., await discord_bot.notify_delisted(mint_address)

            # IMPORTANT: Sleep to respect the 2 QPS rate limit.
            await asyncio.sleep(0.55)
        except Exception as e:
            logger.error(f"Error in reaper task: {e}", exc_info=True)
        finally:
            queue.task_done()

async def process_listing(listing: dict, queue: asyncio.Queue, send_alert: bool = True):
    """
    The complete, atomic pipeline for a single listing:
    1. Fetch ALT data.
    2. Check business logic.
    3. Queue alert for Discord if it's a snipe.
    4. Save the complete record to DB.
    5. Add to the reaper's verification queue if relevant.
    """
    start_time = time.time()
    logger.info(f"Processing: {listing.get('name')} ({listing.get('grading_id')})")
    
    try:
        loop = asyncio.get_running_loop()
        processed_alt_data = await loop.run_in_executor(
            None, alt.get_alt_data, 
            listing['grading_id'], 
            listing.get('grade_num', 0), 
            listing['grading_company']
        )
        
        if not processed_alt_data:
            logger.warning(f"Could not fetch ALT data for {listing.get('name')}. Marking as SKIP.")
            await asyncio.to_thread(database.skip_listing, listing['listing_id'], 'SKIP')
            return

        prices = await loop.run_in_executor(None, utils.get_price_in_both_currencies, listing['price_amount'], listing['price_currency'])
        if not prices:
            logger.error(f"Could not convert price for {listing.get('name')}. Skipping.")
            return

        snipe_details = {**processed_alt_data, 'listing_price_usd': prices['price_usdc']}
        
        # --- Business Logic ---
        alert_level = None
        alt_value = snipe_details.get('alt_value', 0)
        listing_price_usd = snipe_details.get('listing_price_usd', 0)
        alt_confidence = snipe_details.get('confidence', 0)
        cartel_category = 'SKIP'

        if alt_value > 0 and listing_price_usd > 0 and alt_confidence > 60:
            diff_percent = ((listing_price_usd - alt_value) / alt_value) * 100
            if diff_percent <= -30: 
                snipe_details['difference_str'] = f"🟢 {diff_percent:+.2f}%"
                alert_level = 'GOLD'
                cartel_category = 'AUTOBUY'
                # AUTOBUYLOGIC HERE
            else: 
                snipe_details['difference_str'] = f"{diff_percent:+.2f}%"
                if diff_percent <= -20: 
                    alert_level = 'HIGH'
                    cartel_category = 'GOOD'
                elif diff_percent <= -15: 
                    alert_level = 'INFO'
                    cartel_category = 'OK'                    
                
        if alert_level and send_alert:
            await queue.put({'listing_data': listing, 'snipe_details': snipe_details, 'alert_level': alert_level})
       

        await asyncio.to_thread(database.update_listing, listing['listing_id'], snipe_details, cartel_category)
        
        # --- Add to Reaper Queue if not SKIP ---
        if cartel_category != 'SKIP':
            token_mint = listing.get('token_mint')
            if token_mint:
                logger.info(f"Adding {token_mint} to reaper queue (Category: {cartel_category}).")
                await verification_queue.put(token_mint)

        duration = time.time() - start_time
        logger.info(f"Successfully processed {listing.get('name')}. Took {duration:.3f}s. Alert: {alert_level}")

    except Exception as e:
        logger.error(f"Unexpected error while processing {listing.get('name')}: {e}", exc_info=True)

async def initial_population(queue: asyncio.Queue):
    """
    Slowly fetches all ME listings, enriches them, and saves them to the DB.
    This runs only if the database is empty.
    """
    logger.info("Database is empty. Starting full, slow population...")
    all_listings, _ = await asyncio.to_thread(me.fetch_initial_listings) # Assuming you add this back to ME file
    if not all_listings:
        logger.warning("Initial fetch returned no listings.")
        return

    logger.info(f"Found {len(all_listings)} total listings. Starting enrichment process (this will be very slow)...")
    for i, listing in enumerate(all_listings):
        logger.info(f"--- Populating listing {i+1}/{len(all_listings)} ---")
        await asyncio.to_thread(database.save_listing, [listing])
        await process_listing(listing, queue, send_alert=False)
        await asyncio.sleep(3) # Respectful delay
    logger.info("--- Initial population and enrichment complete! ---")

async def watchdog(queue: asyncio.Queue):
    """The main high-speed watchdog loop."""
    logger.info("--- Starting Watchdog ---")
    processed_ids = await asyncio.to_thread(database.get_all_listing_ids)
    logger.info(f"Loaded {len(processed_ids)} previously processed listing IDs.")
    loop = asyncio.get_running_loop()
    
    while True:
        try:
            
            new_listings = await loop.run_in_executor(None, me.fetch_new_listings, processed_ids)
            if new_listings:
                logger.info(f"Found {len(new_listings)} new items!")
                tasks = []
                for listing in new_listings:
                    processed_ids.add(listing['listing_id'])
                    await asyncio.to_thread(database.save_listing, [listing])
                    # The process_listing function now handles adding to the reaper queue internally
                    tasks.append(process_listing(listing, queue, send_alert=True))
                await asyncio.gather(*tasks)
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.critical(f"Unexpected error in watchdog loop: {e}", exc_info=True)
            await asyncio.sleep(10)

async def main():
    """The main entry point for the application."""
    snipe_queue = asyncio.Queue()
    logger.info("--- Sniper booting up ---")
    
    # Initialize DB
    await asyncio.to_thread(database.init_db)

    # Populate the reaper queue with existing items from the DB
    initial_reaper_items = await asyncio.to_thread(database.get_initial_reaper_queue_items)
    for item in initial_reaper_items:
        await verification_queue.put(item)
    
    if not await asyncio.to_thread(database.get_all_listing_ids):
        await initial_population(snipe_queue)

    # Start all background tasks
    discord_task = asyncio.create_task(discord_bot.start_discord_bot(snipe_queue))
    watchdog_task = asyncio.create_task(watchdog(snipe_queue))
    reaper_task = asyncio.create_task(reaper(verification_queue))
    
    await asyncio.gather(discord_task, watchdog_task, reaper_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down sniper.")


