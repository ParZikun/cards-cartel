import os
from dotenv import load_dotenv
import logging
import logging.config
import yaml
import re

# --- Centralized Environment Loading ---
# Load .env.local for local development, otherwise fall back to .env
if os.path.exists('.env.local'):
    load_dotenv(dotenv_path='.env.local')
else:
    load_dotenv()

import time
import asyncio
from database import main as database

# Import the new async functions
from worker.app.core import magic_eden as me
from worker.app.core import alt_data as alt
from worker.app.core import utils as utils
import discord
from worker.app import discord_bot as discord_bot
from datetime import datetime, timezone, timedelta

# Limit the bot to 10 concurrent requests to the ALT API
ALT_API_SEMAPHORE = asyncio.Semaphore(10)

# --- Setup Logging ---
# Get the directory of the current script to build a reliable path to the config file
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, '..', 'logging_config.yaml') # Go up one level to find the config
with open(config_path, 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
logger = logging.getLogger(__name__)
if os.path.exists('.env.local'): logger.info("Loading configuration from .env.local for local testing.")

verification_queue = asyncio.Queue()


# Import the new core modules
from worker.app.core import processor
from worker.app.core import syncer

async def reaper(verification_queue: asyncio.Queue, snipe_queue: asyncio.Queue):
    """Pulls a mint address from the queue, verifies its status, and acts on it."""
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

                    last_analyzed_str = listing.get('last_analyzed_at')
                    last_analyzed_at = None
                    if not last_analyzed_str:
                        last_analyzed_at = datetime.fromtimestamp(0, tz=timezone.utc)
                    elif isinstance(last_analyzed_str, str):
                        last_analyzed_at = datetime.fromisoformat(last_analyzed_str)
                        if last_analyzed_at.tzinfo is None:
                            last_analyzed_at = last_analyzed_at.replace(tzinfo=timezone.utc)
                    elif isinstance(last_analyzed_str, datetime):
                        last_analyzed_at = last_analyzed_str
                        if last_analyzed_at.tzinfo is None:
                            last_analyzed_at = last_analyzed_at.replace(tzinfo=timezone.utc)
                    else:
                        last_analyzed_at = datetime.fromtimestamp(0, tz=timezone.utc)
                    
                    if datetime.now(timezone.utc) - last_analyzed_at > timedelta(hours=24):
                        logger.debug(f"Reaper: Re-analyzing stale listing for {listing.get('name')}.")
                        # Use the processor module
                        found_deal, category = await processor.process_listing(listing, snipe_queue, send_alert=True)
                
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


async def cartel_recheck(queue: asyncio.Queue, timeframe: str, interaction: discord.Interaction):
    """
    Fetches active listings marked as 'SKIP' within a given timeframe and re-processes them.
    """
    logger.info(f"--- Starting a re-check of 'SKIP' listings for timeframe: {timeframe} ---")
    
    time_deltas = {
        "1H": timedelta(hours=1),
        "2H": timedelta(hours=2),
        "6H": timedelta(hours=6),
        "1D": timedelta(days=1),
        "1W": timedelta(weeks=1),
        "1M": timedelta(days=30), # Approximating 1 month as 30 days
    }

    since_timestamp = None
    if timeframe in time_deltas:
        since_timestamp = datetime.now(timezone.utc) - time_deltas[timeframe]

    skipped_listings = await asyncio.to_thread(database.get_skipped_listings, since_timestamp)

    if not skipped_listings:
        logger.warning(f"Re-check initiated for {timeframe}, but no 'SKIP' listings found in that period.")
        await interaction.followup.send(f"ℹ️ No 'SKIP' listings found to re-check for the **{timeframe}** timeframe.", ephemeral=True)
        return

    logger.info(f"Found {len(skipped_listings)} 'SKIP' listings to re-process.")
    
    new_deals_count = 0
    for i, listing in enumerate(skipped_listings):
        logger.info(f"--- Re-processing listing {i+1}/{len(skipped_listings)} ---")
        if await process_listing(listing, queue, send_alert=True):
            new_deals_count += 1
        await asyncio.sleep(0.55)

    processed_count = len(skipped_listings)
    logger.info(f"--- Re-check for timeframe '{timeframe}' complete! ---")
    await interaction.followup.send(
        f"✅ **Re-check Complete!**\n"
        f"Processed **{processed_count}** listings from the **{timeframe}** timeframe.\n"
        f"Found **{new_deals_count}** new deals.",
        ephemeral=True
    )

async def initial_population(queue: asyncio.Queue):
    """
    Slowly fetches all ME listings, enriches them, and saves them to the DB.
    """
    logger.info("Database is empty. Starting full, slow population...")
    
    all_listings, _ = await me.fetch_initial_listings_async()
    if not all_listings:
        logger.warning("Initial fetch returned no listings.")
        return
    
    logger.info(f"Found {len(all_listings)} total listings. Starting enrichment process...")
    
    for i, listing in enumerate(all_listings):
        logger.info(f"--- Populating listing {i+1}/{len(all_listings)} ---")
        await asyncio.to_thread(database.save_listing, [listing])
        await processor.process_listing(listing, queue, send_alert=False)
        await asyncio.sleep(1)
            
    logger.info("--- Initial population and enrichment complete! ---")

async def watchdog(queue: asyncio.Queue):
    """The main high-speed watchdog loop."""
    logger.info("--- Starting Watchdog ---")
    processed_ids = await asyncio.to_thread(database.get_all_listing_ids)
    logger.info(f"Loaded {len(processed_ids)} previously processed listing IDs.")
    
    while True:
        try:
            new_listings = await me.fetch_new_listings_async(processed_ids)
            if new_listings:
                logger.info(f"Found {len(new_listings)} new items!")
                
                tasks = []
                for listing in new_listings:
                    processed_ids.add(listing['listing_id'])
                    await asyncio.to_thread(database.save_listing, [listing])
                    tasks.append(processor.process_listing(listing, queue, send_alert=True))
                await asyncio.gather(*tasks)

            await asyncio.sleep(0.3)
        except Exception as e:
            logger.critical(f"Unexpected error in watchdog loop: {e}", exc_info=True)
            await asyncio.sleep(10)

async def main():
    """The main entry point for the application."""
    
    snipe_queue = asyncio.Queue()
    logger.info("--- Sniper booting up ---")
    
    await asyncio.to_thread(database.init_db)

    initial_reaper_items = await asyncio.to_thread(database.get_initial_reaper_queue_items)
    for item in initial_reaper_items:
        await verification_queue.put(item)
    
    if not await asyncio.to_thread(database.get_all_listing_ids):
        await initial_population(snipe_queue)

    discord_task = asyncio.create_task(discord_bot.start_discord_bot(snipe_queue, recheck_skipped_callback=lambda timeframe, interaction: cartel_recheck(snipe_queue, timeframe, interaction)))
    watchdog_task = asyncio.create_task(watchdog(snipe_queue))
    reaper_task = asyncio.create_task(reaper(verification_queue, snipe_queue))
    
    await asyncio.gather(discord_task, watchdog_task, reaper_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down sniper.")