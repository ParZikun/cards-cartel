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
from worker.app.core import syncer

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


async def listing_consumer_worker(worker_id: int, listing_queue: asyncio.PriorityQueue, snipe_queue: asyncio.Queue):
    """
    Consumer task that pulls listings from the queue and processes them.
    Multiple of these will run in parallel to handle high-latency Alt processing.
    """
    logger.debug(f"Consumer {worker_id} started.")
    while True:
        try:
            # Unpack the 3-element tuple (priority, count, listing)
            priority, _, listing = await listing_queue.get()
            
            # Process the listing
            # NOTE: fast_mode will be enabled inside processor based on context or we update processor to handle it.
            # ideally processor decides.
            
            await processor.process_listing(listing, snipe_queue, send_alert=True)
            
            listing_queue.task_done()
        except Exception as e:
            logger.error(f"Consumer {worker_id} error: {e}", exc_info=True)
            # Prevent rapid crash loops
            await asyncio.sleep(1)

async def reaper(verification_queue: asyncio.Queue, listing_queue: asyncio.PriorityQueue):
    """
    Pulls a mint address from the verification queue.
    If it needs analysis, puts it into the processing queue with LOWER priority.
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


async def cartel_recheck(queue: asyncio.PriorityQueue, timeframe: str, interaction: discord.Interaction):
    """
    Fetches active listings marked as 'SKIP' and queues them for processing.
    """
    logger.info(f"--- Starting a re-check of 'SKIP' listings for timeframe: {timeframe} ---")
    
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

    if not skipped_listings:
        await interaction.followup.send(f"ℹ️ No 'SKIP' listings found to re-check.", ephemeral=True)
        return

    logger.info(f"Queuing {len(skipped_listings)} 'SKIP' listings for re-check (Priority 1).")
    
    for listing in skipped_listings:
        # Priority 1 for re-checks
        await queue.put((1, next(queue_tie_breaker), listing))
        
    await interaction.followup.send(
        f"✅ **Re-check Queued!**\n"
        f"Queued **{len(skipped_listings)}** listings for background processing.",
        ephemeral=True
    )

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

async def watchdog(queue: asyncio.PriorityQueue):
    """
    The main high-speed watchdog loop.
    True Producer: Fetches from ME and dumps to Queue. Never waits for processing.
    """
    logger.info("--- Starting Watchdog (Producer) ---")
    processed_ids = await asyncio.to_thread(database.get_all_listing_ids)
    logger.info(f"Loaded {len(processed_ids)} previously processed listing IDs.")
    
    while True:
        try:
            start_time = time.time()
            # Fetch new listings
            blacklist = database.get_global_blacklist()
            new_listings = await me.fetch_new_listings_async(processed_ids, blacklisted_keywords=blacklist)
            
            if new_listings:
                logger.info(f"Watchdog found {len(new_listings)} new items! Queuing at Priority 0.")
                
                for listing in new_listings:
                    processed_ids.add(listing['listing_id'])
                    await asyncio.to_thread(database.save_listing, [listing])
                    
                    # Push to Queue with Priority 0 (Highest)
                    await queue.put((0, next(queue_tie_breaker), listing))
            
            # Adaptive Sleep? 
            # If we took long to fetch, sleep less. 
            # Ideally we want to poll as fast as ME rate limits allow.
            # Fixed 300ms is aggressive but good.
            await asyncio.sleep(0.3)
            
        except Exception as e:
            logger.critical(f"Make sure you have internet connection error in watchdog loop: {e}", exc_info=True)
            await asyncio.sleep(5)

async def main():
    """The main entry point for the application."""
    
    # Queue for Discord Alerts (results)
    snipe_queue = asyncio.Queue()
    logger.info("--- Sniper booting up ---")
    
    await asyncio.to_thread(database.init_db)

    # Convert initial reaper items to verification queue
    initial_reaper_items = await asyncio.to_thread(database.get_initial_reaper_queue_items)
    for item in initial_reaper_items:
        await verification_queue.put(item)
    
    # DB Check for initial pop
    if not await asyncio.to_thread(database.get_all_listing_ids):
        # We spawn this as a task so it doesn't block startup
        asyncio.create_task(initial_population(listing_processing_queue))

    # --- Start Workers ---
    
    # 1. Discord Bot (Consumers snipe_queue)
    discord_task = asyncio.create_task(discord_bot.start_discord_bot(
        snipe_queue, 
        recheck_skipped_callback=lambda timeframe, interaction: cartel_recheck(listing_processing_queue, timeframe, interaction)
    ))
    
    # 2. Watchdog (Producer for listing_processing_queue - Priority 0)
    watchdog_task = asyncio.create_task(watchdog(listing_processing_queue))
    
    # 3. Reaper (Producer for listing_processing_queue - Priority 1 via verification_queue)
    reaper_task = asyncio.create_task(reaper(verification_queue, listing_processing_queue))
    
    # 4. Listing Consumers (The Worker Pool)
    # Critical: Determine pool size. ALT_API_SEMAPHORE is 10.
    # If we have 20 workers, 10 will be active on Alt, 10 waiting. This ensures Semaphore is always maxed.
    num_workers = 25
    consumer_tasks = []
    for i in range(num_workers):
        t = asyncio.create_task(listing_consumer_worker(i, listing_processing_queue, snipe_queue))
        consumer_tasks.append(t)
    
    logger.info(f"Started {num_workers} consumer workers.")
    
    await asyncio.gather(discord_task, watchdog_task, reaper_task, *consumer_tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down sniper.")