import os
from dotenv import load_dotenv
import logging
import logging.config
import yaml
import re

# --- Centralized Environment Loading ---
if os.path.exists('.env.local'):
    load_dotenv(dotenv_path='.env.local')
else:
    load_dotenv()

import time
import asyncio
from database import main as database

from worker.app.core import magic_eden as me
from worker.app.core import alt_data as alt
from worker.app.core import utils as utils
import discord
from worker.app import discord_bot as discord_bot
from datetime import datetime, timezone, timedelta

# Import the new core modules
from worker.app.core import processor
# from worker.app.core import syncer # Unused

# --- Setup Logging ---
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, '..', 'logging_config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
logger = logging.getLogger(__name__)
if os.path.exists('.env.local'): logger.info("Loading configuration from .env.local for local testing.")

import itertools

# Queues
# verification_queue: Managed by reaper for periodic re-checks of existing DB items
verification_queue = asyncio.Queue()

# listing_processing_queue: The main pipeline. 
# Priority 0: New High-Speed Listings (Watchdog)
# Priority 1: Re-checks (Reaper/Manual)
# Priority 2: Initial Population / Backlog
listing_processing_queue = asyncio.PriorityQueue()
queue_tie_breaker = itertools.count() # Global counter to break ties in PriorityQueue


async def listing_consumer_worker(worker_id: int, listing_queue: asyncio.PriorityQueue, snipe_queue: asyncio.Queue, verification_queue: asyncio.Queue):
    """
    Consumer task that pulls listings from the queue and processes them.
    Multiple of these will run in parallel to handle high-latency Alt processing.
    """
    logger.debug(f"Consumer {worker_id} started.")
    while True:
        try:
            # Unpack the 3-element tuple (priority, count, listing)
            priority, _, listing = await listing_queue.get()
            logger.info(f"👉 Consumer {worker_id} dequeued: {listing.get('name', 'Unknown')} | Price: {listing.get('price_amount')}")
            
            # Process the listing
            # NOTE: fast_mode will be enabled inside processor based on context or we update processor to handle it.
            # ideally processor decides.
            
            found_deal, category = await processor.process_listing(listing, snipe_queue, send_alert=True)
            
            # CRITICAL FIX: Add valuable finds to reaper (verification_queue) for continuous monitoring.
            if category in ['AUTOBUY', 'GOOD', 'OK'] and listing.get('token_mint'):
                logger.debug(f"Consumer {worker_id}: Adding {listing.get('name')} ({category}) to Reaper for monitoring.")
                await verification_queue.put(listing['token_mint'])
            
            listing_queue.task_done()
        except Exception as e:
            logger.error(f"Consumer {worker_id} error: {e}", exc_info=True)
            await snipe_queue.put({'alert_level': 'LOG', 'reason': f"⚠️ **Worker Error** (ID {worker_id}): {e}"})
            # Prevent rapid crash loops
            await asyncio.sleep(1)

async def reaper(verification_queue: asyncio.Queue, listing_processing_queue: asyncio.PriorityQueue):
    """
    [Safety Net] Background Maintenance Task.
    - Default State: IDLE (Waits for items in 'verification_queue').
    - Trigger: Manual rechecks from Discord or specific edge cases.
    - Action: Checks ME status (Throttled). Updates price in DB or marks as sold.
    - Output: If valid & active, puts into 'listing_processing_queue' (Low Priority) for analysis.
    """
    logger.info("--- Starting Reaper ---")
    while True:
        mint_address = None
        try:
            mint_address = await verification_queue.get()
            card_data = await me.check_listing_status_async(mint_address)
            
            if isinstance(card_data, dict) and card_data.get('listStatus') == "listed":
                listing = await asyncio.to_thread(database.get_listing_by_mint, mint_address)
                if listing:
                    # Update listing with fresh price from ME
                    fresh_price = card_data.get('price')
                    if fresh_price:
                        listing['price_amount'] = float(fresh_price)
                        # Minimal DB update for price
                        await asyncio.to_thread(database.update_listing_details, listing['listing_id'], {'price_amount': float(fresh_price)})

                    last_analyzed_str = listing.get('last_analyzed_at')
                    last_analyzed_at = None
                    if not last_analyzed_str:
                        last_analyzed_at = datetime.fromtimestamp(0, tz=timezone.utc)
                    elif isinstance(last_analyzed_str, str):
                        last_analyzed_at = datetime.fromisoformat(last_analyzed_str.replace('Z', '+00:00'))
                        if last_analyzed_at.tzinfo is None:
                            last_analyzed_at = last_analyzed_at.replace(tzinfo=timezone.utc)
                    elif isinstance(last_analyzed_str, datetime):
                        last_analyzed_at = last_analyzed_str
                        if last_analyzed_at.tzinfo is None:
                            last_analyzed_at = last_analyzed_at.replace(tzinfo=timezone.utc)
                    else:
                        last_analyzed_at = datetime.fromtimestamp(0, tz=timezone.utc)
                    
                    if datetime.now(timezone.utc) - last_analyzed_at > timedelta(hours=24):
                        logger.debug(f"Reaper: Queueing stale listing {listing.get('name')} for analysis (Priority 1).")
                        # Put in main queue with Priority 1 (Lower than new items)
                        await listing_queue.put((1, next(queue_tie_breaker), listing))
                
                await verification_queue.put(mint_address)
            else:
                logger.info(f"Reaper: Listing {mint_address} is no longer active. Updating DB.")
                await asyncio.to_thread(database.update_listing_status, mint_address, False)

            await asyncio.sleep(0.55)
        except Exception as e:
            logger.error(f"Error in reaper task: {e}", exc_info=True)
        finally:
            if mint_address is not None:
                verification_queue.task_done()


async def cartel_recheck(listing_queue: asyncio.PriorityQueue, verification_queue: asyncio.Queue, timeframe: str, interaction: discord.Interaction):
    """
    1. Refreshes active 'DEALS' (GOOD, OK, AUTOBUY) by queuing them for Reaper verification.
    2. Fetches 'SKIP' listings within timeframe and queues them for full re-processing.
    """
    logger.info(f"--- Starting Cartel Recheck (Deals + Skips) for timeframe: {timeframe} ---")
    
    # --- Step 1: Refresh Active Deals ---
    active_deals = await asyncio.to_thread(database.get_initial_reaper_queue_items)
    if active_deals:
        logger.info(f"Adding {len(active_deals)} active deals to verification queue (Reaper).")
        for mint in active_deals:
            await verification_queue.put(mint)
            
    # --- Step 2: Recheck Skipped Listings ---
    time_deltas = {
        "1H": timedelta(hours=1),
        "2H": timedelta(hours=2),
        "6H": timedelta(hours=6),
        "1D": timedelta(days=1),
        "1W": timedelta(weeks=1),
        "1M": timedelta(days=30),
    }

    since_timestamp = None
    if timeframe in time_deltas:
        since_timestamp = datetime.now(timezone.utc) - time_deltas[timeframe]

    skipped_listings = await asyncio.to_thread(database.get_skipped_listings, since_timestamp)

    msg = f"🔄 **Recheck Started!**\n1. Queued **{len(active_deals)}** active deals for live status check.\n"

    if not skipped_listings:
        msg += f"2. No 'SKIP' listings found to re-process."
    else:
        msg += f"2. Queued **{len(skipped_listings)}** 'SKIP' listings for re-analysis (Priority 1)."
        logger.info(f"Queuing {len(skipped_listings)} 'SKIP' listings for re-check (Priority 1).")
        for listing in skipped_listings:
            await listing_queue.put((1, next(queue_tie_breaker), listing))
        
    await interaction.followup.send(msg, ephemeral=True)

async def initial_population(queue: asyncio.PriorityQueue):
    """
    Slowly fetches all ME listings and queues them.
    """
    logger.info("Database is empty. Starting full, slow population...")
    
    blacklist = database.get_global_blacklist()
    all_listings, _ = await me.fetch_initial_listings_async(blacklisted_keywords=blacklist)
    if not all_listings:
        logger.warning("Initial fetch returned no listings.")
        return
    
    logger.info(f"Found {len(all_listings)} total listings. Queuing with Priority 2 (Low)...")
    
    for i, listing in enumerate(all_listings):
        await asyncio.to_thread(database.save_listing, [listing])
        # Priority 2 for initial population
        await queue.put((2, next(queue_tie_breaker), listing))
        # No sleep needed here, the consumers effectively rate limit themselves by their processing speed.
        # But to avoid memory spike we can throttle producer slightly
        await asyncio.sleep(0.01) 
            
    logger.info("--- Initial population queued! ---")

async def watchdog(queue: asyncio.PriorityQueue, alert_queue: asyncio.Queue):
    """
    The main high-speed watchdog loop.
    True Producer: Fetches from ME and dumps to Queue. Never waits for processing.
    """
    logger.info("--- Starting Watchdog (Producer) ---")
    
    # CRITICAL: initialized as Dict[mint, price]
    processed_cache = await asyncio.to_thread(database.get_all_listing_cache)
    logger.info(f"Loaded {len(processed_cache)} previously processed items (with prices).")
    
    # CRITICAL: signature-based deduplication for Activity Feed
    processed_signatures = set()

    # True Parallelism: Two independent loops feeding the same queue
    await asyncio.gather(
        watchdog_activity_loop(processed_cache, processed_signatures, queue, alert_queue),
        watchdog_idxv2_loop(processed_cache, queue, alert_queue)
    )

async def watchdog_activity_loop(processed_cache: dict, processed_signatures: set, queue: asyncio.PriorityQueue, alert_queue: asyncio.Queue):
    """
    [Loop A] Activity Feed Monitor
    - Interval: 1.5s (High Speed).
    - Role: Catches events in real-time. Backup for Time Travel.
    """
    logger.info("--- 🟢 Starting Activity Monitor (1.5s) ---")
    while True:
        try:
            blacklist = database.get_global_blacklist()
            # This function modifies processed_cache in-place to dedup
            new_listings, sold_mints = await me.fetch_new_listings_async(
                processed_cache, 
                processed_signatures=processed_signatures,
                blacklisted_keywords=blacklist
            )
            
            if sold_mints:
                logger.debug(f"[Activity] Found {len(sold_mints)} sold items. Syncing DB...")
                for mint in sold_mints:
                     await asyncio.to_thread(database.update_listing_status, mint, False)
            
            if new_listings:
                logger.info(f"⚡ [Activity] Found {len(new_listings)} NEW items!")
                for listing in new_listings:
                    await process_and_queue_listing(listing, queue)
            
            await asyncio.sleep(1.5)
            
        except Exception as e:
            if "429" in str(e):
                 logger.error("429 Rate Limit in Activity Monitor - Backing off!")
                 await alert_queue.put({'alert_level': 'LOG', 'reason': f"⚠️ **Rate Limit Hit** (Activity Loop): {e}"})
                 await asyncio.sleep(10)
            else:
                 logger.error(f"[Activity] Monitor error: {e}")
                 await alert_queue.put({'alert_level': 'LOG', 'reason': f"⚠️ **Error** (Activity Loop): {e}"})
                 await asyncio.sleep(5)

async def watchdog_idxv2_loop(processed_cache: dict, queue: asyncio.PriorityQueue, alert_queue: asyncio.Queue):
    """
    [Loop B] Idxv2 Feed Monitor
    - Interval: 2.0s (Safety Mode).
    - Role: Main fast feed. Fetches partial/full data.
    """
    logger.info("--- 🚀 Starting Idxv2 Monitor (2.0s) ---")
    while True:
        try:
            blacklist = database.get_global_blacklist()
            # This function also modifies processed_cache in-place
            new_listings, count = await me.fetch_latest_listings_async(processed_cache, blacklisted_keywords=blacklist)
            
            if count > 0:
                logger.info(f"🔥 [Idxv2] Found {count} NEW items!")
                for listing in new_listings:
                    await process_and_queue_listing(listing, queue)
            
            await asyncio.sleep(2.0)
            
        except Exception as e:
            if "429" in str(e):
                 logger.error("429 Rate Limit in Idxv2 Monitor - Backing off!")
                 await alert_queue.put({'alert_level': 'LOG', 'reason': f"⚠️ **Rate Limit Hit** (Idxv2 Loop): {e}"})
                 await asyncio.sleep(10)
            else:
                 logger.error(f"[Idxv2] Monitor error: {e}")
                 await alert_queue.put({'alert_level': 'LOG', 'reason': f"⚠️ **Error** (Idxv2 Loop): {e}"})
                 await asyncio.sleep(5)

async def process_and_queue_listing(listing: dict, queue: asyncio.PriorityQueue):
    """Helper to save and queue a listing."""
    # listing['listing_id'] is already ensuring it's not in processed_ids via the fetch functions
    logger.info(f"📥 [Queue] Enqueueing: {listing.get('name', 'Unknown')} | {listing.get('price_amount', 0)} {listing.get('price_currency', 'SOL')}")
    await asyncio.to_thread(database.save_listing, [listing])
    await queue.put((0, next(queue_tie_breaker), listing))

async def full_database_refresh():
    """
    Fetches all active listings from DB and refreshes their status/price from ME API.
    Runs sequentially to avoid rate limits before the high-speed watchdog starts.
    """
    logger.info("--- 🔄 Starting Full Database Refresh (Pre-flight Check) ---")
    active_mints = await asyncio.to_thread(database.get_initial_reaper_queue_items)
    
    if not active_mints:
        logger.info("No active listings found in DB. Clean slate.")
        return

    logger.info(f"Checking {len(active_mints)} active listings one by one... (Safety Mode)")
    
    # We use a limited semaphore here too, or just sequential loop.
    # Since we want to be safe, sequential with small sleep is fine, or gather withsemaphore.
    # me.check_listing_status_async already uses the GLOBAL SEMAPHORE (Limit 5).
    # so we can use gather here safely!
    
    tasks = []
    for mint in active_mints:
        tasks.append(reaper_check_logic(mint))
        
    # Process in chunks to show progress? Or just all at once (limited by semaphore)
    # 5 concurrent requests approx 2/s = 200 items take 100s. 
    # If 200 items, we might want chunks.
    
    CHUNK_SIZE = 50
    for i in range(0, len(tasks), CHUNK_SIZE):
        chunk = tasks[i:i + CHUNK_SIZE]
        await asyncio.gather(*chunk)
        logger.info(f"Refreshed batch {i}-{i+len(chunk)}/{len(tasks)}")
        await asyncio.sleep(1) # Cooldown between chunks
        
    logger.info("--- ✅ Full Database Refresh Complete! Starting Watchdog... ---")

async def reaper_check_logic(mint_address: str):
    """
    Helper for database refresh that mimics reaper logic but doesn't loop.
    """
    try:
        card_data = await me.check_listing_status_async(mint_address)
        
        if isinstance(card_data, dict) and card_data.get('listStatus') == "listed":
            # Update price if needed
            fresh_price = card_data.get('price')
            if fresh_price:
                 logger.info(f"Checking {mint_address[:8]}... Price: {fresh_price}")
                 await asyncio.to_thread(database.update_listing_details_by_mint, mint_address, {'price_amount': float(fresh_price)})
        else:
            # Delisted
            if card_data != "not_found": # if not_found, effectively delisted or bad mint
                 logger.info(f"Pre-flight: Listing {mint_address} is no longer active. Marking inactive.")
                 await asyncio.to_thread(database.update_listing_status, mint_address, False)
            elif card_data == "not_found":
                 logger.info(f"Pre-flight: Listing {mint_address} not found on ME. Marking inactive.")
                 await asyncio.to_thread(database.update_listing_status, mint_address, False)

    except Exception as e:
        logger.warning(f"Error refreshing {mint_address}: {e}")

async def main():
    """The main entry point for the application."""
    
    # Queue for Discord Alerts (results)
    snipe_queue = asyncio.Queue()
    
    # Configure Logging Levels
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    logger.info("--- Sniper booting up ---")
    
    await asyncio.to_thread(database.init_db)
    
    # --- PHASE 1: Pre-flight Sync (User Requested) ---
    await full_database_refresh()

    # NOTE: We DO NOT populate verification_queue here anymore.
    # The full_database_refresh has just checked everything.
    # The Reaper will wait for new signals from Watchdog or User.
    
    # DB Check for initial pop

    
    # --- Start Workers ---
    
    # DB Check for initial pop
    if not await asyncio.to_thread(database.get_all_listing_cache):
        # We spawn this as a task so it doesn't block startup
        asyncio.create_task(initial_population(listing_processing_queue))

    # --- Start Workers ---
    
    # 1. Discord Bot (Consumers snipe_queue)
    discord_task = asyncio.create_task(discord_bot.start_discord_bot(
        snipe_queue, 
        recheck_skipped_callback=lambda timeframe, interaction: cartel_recheck(listing_processing_queue, verification_queue, timeframe, interaction)
    ))
    
    # 2. Watchdog (Producer for listing_processing_queue - Priority 0)
    # Passed snipe_queue for System Logs (e.g. Rate Limits)
    watchdog_task = asyncio.create_task(watchdog(listing_processing_queue, snipe_queue))
    
    # 3. Reaper (Producer for listing_processing_queue - Priority 1 via verification_queue)
    reaper_task = asyncio.create_task(reaper(verification_queue, listing_processing_queue))
    
    # 4. Listing Consumers (The Worker Pool)
    # Critical: Determine pool size. ALT_API_SEMAPHORE is 10.
    # If we have 20 workers, 10 will be active on Alt, 10 waiting. This ensures Semaphore is always maxed.
    # REDUCED to 5 to avoid ME Rate Limits (429) without API Key
    num_workers = 5
    consumer_tasks = []
    for i in range(num_workers):
        t = asyncio.create_task(listing_consumer_worker(i, listing_processing_queue, snipe_queue, verification_queue))
        consumer_tasks.append(t)
    
    logger.info(f"Started {num_workers} consumer workers.")
    
    await asyncio.gather(discord_task, watchdog_task, reaper_task, *consumer_tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down sniper.")