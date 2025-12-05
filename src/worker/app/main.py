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
                        await process_listing(listing, snipe_queue, send_alert=True)
                
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

async def process_listing(listing: dict, queue: asyncio.Queue, send_alert: bool = True) -> bool:
    """
    The complete, atomic pipeline for a single listing.
    Returns True if a new deal was found, False otherwise.
    """
    skip_alt_fetch = False
    
    # If this card is already in our database, check when we last analyzed it.
    if 'last_analyzed_at' in listing and listing['last_analyzed_at'] is not None:
        try:
            # Convert last_analyzed_at (which may be a string) to a datetime object
            last_analyzed_str = str(listing['last_analyzed_at']).replace('Z', '+00:00')
            last_analyzed_dt = datetime.fromisoformat(last_analyzed_str)

            # Ensure the datetime is timezone-aware for comparison
            if last_analyzed_dt.tzinfo is None:
                last_analyzed_dt = last_analyzed_dt.replace(tzinfo=timezone.utc)

            # If it was analyzed in the last 7 days, we can skip the ALT API call
            if (datetime.now(timezone.utc) - last_analyzed_dt).days < 7:
                logger.debug(f"CACHE HIT: Skipping ALT analysis for {listing.get('name')} (last analyzed {last_analyzed_dt.strftime('%Y-%m-%d')})")
                skip_alt_fetch = True
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse 'last_analyzed_at' timestamp '{listing['last_analyzed_at']}'. Re-analyzing. Error: {e}")
            
    start_time = time.time()
    logger.debug(f"Processing: {listing.get('name')} ({listing.get('grading_id')})")
    
    try:
        # --- 1. Fetch ALT Data (or use cached) ---
        processed_alt_data = None
        
        if skip_alt_fetch:
            # Use existing data from the listing object
            processed_alt_data = {
                'alt_asset_id': listing.get('alt_asset_id'),
                'alt_value': listing.get('alt_value', 0),
                'avg_price': listing.get('avg_price', 0),
                'supply': listing.get('supply', 0),
                'lower_bound': listing.get('alt_value_lower_bound', 0),
                'upper_bound': listing.get('alt_value_upper_bound', 0),
                'confidence': listing.get('alt_value_confidence', 0)
            }
        else:
            t0 = time.time()
            async with ALT_API_SEMAPHORE:
                processed_alt_data = await alt.get_alt_data_async(
                    listing['grading_id'], 
                    listing.get('grade_num', 0), 
                    listing['grading_company']
                )
            t1 = time.time()
            logger.debug(f"ALT data fetch took: {t1 - t0:.3f}s")
        
        if not processed_alt_data:
            logger.warning(f"Could not fetch ALT data for {listing.get('name')}. Marking as SKIP.")
            await asyncio.to_thread(database.skip_listing, listing['listing_id'], 'SKIP')
            return False

        # --- 2. Convert Price ---
        t0 = time.time()
        prices = await utils.get_price_in_both_currencies(listing['price_amount'], listing['price_currency'])
        t1 = time.time()
        logger.debug(f"Price conversion took: {t1 - t0:.3f}s")

        if not prices:
            logger.error(f"Could not convert price for {listing.get('name')}. Skipping.")
            return False

        snipe_details = {**processed_alt_data, 'listing_price_usd': prices['price_usdc']}
        
        # --- 3. Determine Alert Level ---
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
            else: 
                snipe_details['difference_str'] = f"{diff_percent:+.2f}%"
                if diff_percent <= -20: 
                    alert_level = 'HIGH'
                    cartel_category = 'GOOD'
                elif diff_percent <= -15: 
                    alert_level = 'INFO'
                    cartel_category = 'OK'
        
        # --- 4. Queue Alert and Update DB ---
        found_deal = False
        if alert_level and send_alert:
            await queue.put({
                'listing_data': listing, 
                'snipe_details': snipe_details, 
                'alert_level': alert_level,
                'duration': time.time() - start_time # Use overall duration for the alert
            })
            found_deal = True
       
        t0 = time.time()
        await asyncio.to_thread(database.update_listing, listing['listing_id'], snipe_details, cartel_category)
        t1 = time.time()
        logger.debug(f"Database update took: {t1 - t0:.3f}s")
        
        if cartel_category != 'SKIP':
            token_mint = listing.get('token_mint')
            if token_mint:
                logger.debug(f"Adding {token_mint} to reaper queue (Category: {cartel_category}).")
                await verification_queue.put(token_mint)

        total_duration = time.time() - start_time
        if alert_level:
             logger.info(f"Successfully processed {listing.get('name')}. Took {total_duration:.3f}s. Alert: {alert_level}")
        else:
             logger.debug(f"Processed {listing.get('name')} (No Alert). Took {total_duration:.3f}s.")
        return found_deal

    except Exception as e:
        logger.error(f"Unexpected error while processing {listing.get('name')}: {e}", exc_info=True)
        return False

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
        await process_listing(listing, queue, send_alert=False)
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