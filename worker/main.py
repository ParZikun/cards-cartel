import os
from dotenv import load_dotenv
import logging
import logging.config
import yaml

# --- Centralized Environment Loading ---
# Load .env.local for local development, otherwise fall back to .env
if os.path.exists('.env.local'):
    load_dotenv(dotenv_path='.env.local')
else:
    load_dotenv()

import time
import asyncio
from database import core as database

# --- Tracing Imports ---
from opentelemetry import trace
from .core import tracing

# Import the new async functions
from .core import magic_eden as me
from .core import alt_data as alt
from .core import utils as utils
from . import discord_bot as discord_bot
from datetime import datetime, timezone, timedelta

# --- Setup Logging ---
with open('logging_config.yaml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
logger = logging.getLogger(__name__)
if os.path.exists('worker/.env.local'): logger.info("Loading configuration from .env.local for local testing.")

# --- Setup Tracing ---
# This will be used to create spans
tracer = tracing.get_tracer(__name__)

verification_queue = asyncio.Queue()

async def reaper(verification_queue: asyncio.Queue, snipe_queue: asyncio.Queue):
    """Pulls a mint address from the queue, verifies its status, and acts on it."""
    logger.info("--- Starting Reaper ---")
    while True:
        mint_address = None
        iteration_span = None
        try:
            # Start a new span for each item pulled from the queue
            with tracer.start_as_current_span("reaper_iteration") as iteration_span:
                mint_address = await verification_queue.get()
                iteration_span.set_attribute("mint_address", mint_address)

                card_data = await me.check_listing_status_async(mint_address)
                
                # Ensure the status attribute is always a string and never None.
                status_attribute = "unknown"
                if isinstance(card_data, dict): status_attribute = card_data.get('listStatus', 'unknown')
                elif card_data is not None: status_attribute = str(card_data)
                iteration_span.set_attribute("listing.status", status_attribute)
            
                # Only treat it as "listed" if the returned data is a dict containing that key.
                if isinstance(card_data, dict) and card_data.get('listStatus') == "listed":
                    # If still listed, check if it needs re-analysis
                    listing = await asyncio.to_thread(database.get_listing_by_mint, mint_address)
                    if listing:
                        last_analyzed_str = listing.get('last_analyzed_at')
                        # The timestamp from DB is naive, so we assume UTC
                        # Safely handle missing or non-string timestamps
                        last_analyzed_at = None
                        if not last_analyzed_str:
                            # treat missing timestamp as very old so it will be re-analyzed
                            last_analyzed_at = datetime.fromtimestamp(0, tz=timezone.utc)
                        elif isinstance(last_analyzed_str, str):
                            # parse ISO string and ensure timezone-aware (assume UTC)
                            last_analyzed_at = datetime.fromisoformat(last_analyzed_str)
                            if last_analyzed_at.tzinfo is None:
                                last_analyzed_at = last_analyzed_at.replace(tzinfo=timezone.utc)
                        elif isinstance(last_analyzed_str, datetime):
                            last_analyzed_at = last_analyzed_str
                            if last_analyzed_at.tzinfo is None:
                                last_analyzed_at = last_analyzed_at.replace(tzinfo=timezone.utc)
                        else:
                            # Fallback: treat as very old
                            last_analyzed_at = datetime.fromtimestamp(0, tz=timezone.utc)
                        
                        if datetime.now(timezone.utc) - last_analyzed_at > timedelta(hours=24):
                            logger.info(f"Reaper: Re-analyzing stale listing for {listing.get('name')}.")
                            iteration_span.set_attribute("listing.reanalyzed", True)
                            await process_listing(listing, snipe_queue, send_alert=True)
                    
                    # Put it back in the queue for future checks
                    await verification_queue.put(mint_address)
                else:
                    logger.info(f"Reaper: Listing {mint_address} is no longer active. Updating DB.")
                    await asyncio.to_thread(database.update_listing_status, mint_address, False)

                await asyncio.sleep(0.55)
        except Exception as e:
            logger.error(f"Error in reaper task: {e}", exc_info=True)
            # Ensure the span is recorded in case of an error
            if iteration_span is not None:
                iteration_span.record_exception(e)
                iteration_span.set_status(trace.Status(trace.StatusCode.ERROR))
        finally:
            # Only call task_done if an item was actually retrieved from the queue
            if mint_address is not None:
                verification_queue.task_done()

@tracer.start_as_current_span("process_listing")
async def process_listing(listing: dict, queue: asyncio.Queue, send_alert: bool = True):
    """
    The complete, atomic pipeline for a single listing.
    """
    start_time = time.time()
    logger.info(f"Processing: {listing.get('name')} ({listing.get('grading_id')})")
    
    current_span = trace.get_current_span()
    # Add key details to the span to make it searchable
    # Ensure we never pass None to set_attribute by coercing to safe types/defaults
    listing_id_attr = str(listing.get('listing_id')) if listing.get('listing_id') is not None else "unknown"
    listing_name_attr = listing.get('name') or "unknown"
    listing_grade_id_attr = str(listing.get('grading_id')) if listing.get('grading_id') is not None else "unknown"
    current_span.set_attribute("listing.id", listing_id_attr)
    current_span.set_attribute("listing.name", listing_name_attr)
    current_span.set_attribute("listing.grade_id", listing_grade_id_attr)

    try:
        processed_alt_data = await alt.get_alt_data_async(
            listing['grading_id'], 
            listing.get('grade_num', 0), 
            listing['grading_company']
        )
        
        if not processed_alt_data:
            logger.warning(f"Could not fetch ALT data for {listing.get('name')}. Marking as SKIP.")
            await asyncio.to_thread(database.skip_listing, listing['listing_id'], 'SKIP')
            current_span.set_attribute("listing.status", "SKIPPED_NO_ALT_DATA")
            return

        prices = await utils.get_price_in_both_currencies(listing['price_amount'], listing['price_currency'])
        if not prices:
            logger.error(f"Could not convert price for {listing.get('name')}. Skipping.")
            current_span.set_attribute("listing.status", "SKIPPED_NO_PRICE_DATA")
            return

        snipe_details = {**processed_alt_data, 'listing_price_usd': prices['price_usdc']}
        
        # Create a dedicated span for the business logic to time it separately
        with tracer.start_as_current_span("business_logic") as business_span:
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
            
            # Add results to the business logic span
            business_span.set_attribute("alert_level", str(alert_level))
            business_span.set_attribute("cartel_category", cartel_category)

        current_span.set_attribute("alert_level", str(alert_level))
        current_span.set_attribute("cartel_category", cartel_category)

        # Calculate duration before sending to Discord queue
        duration = time.time() - start_time
                
        if alert_level and send_alert:
            await queue.put({
                'listing_data': listing, 
                'snipe_details': snipe_details, 
                'alert_level': alert_level,
                'duration': duration
            })
       
        await asyncio.to_thread(database.update_listing, listing['listing_id'], snipe_details, cartel_category)
        
        if cartel_category != 'SKIP':
            token_mint = listing.get('token_mint')
            if token_mint:
                logger.info(f"Adding {token_mint} to reaper queue (Category: {cartel_category}).")
                await verification_queue.put(token_mint)

        logger.info(f"Successfully processed {listing.get('name')}. Took {duration:.3f}s. Alert: {alert_level}")
        current_span.set_attribute("processing_duration_ms", duration * 1000)

    except Exception as e:
        logger.error(f"Unexpected error while processing {listing.get('name')}: {e}", exc_info=True)
        current_span.record_exception(e)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR))

@tracer.start_as_current_span("recheck_all_listings")
async def recheck_all_listings(queue: asyncio.Queue):
    """
    Fetches all active listings from the database and re-processes them.
    """
    logger.info("--- Starting a full re-check of all active listings ---")
    current_span = trace.get_current_span()
    
    active_listings = await asyncio.to_thread(database.get_all_active_listings)
    if not active_listings:
        logger.warning("Re-check initiated, but no active listings found.")
        return

    logger.info(f"Found {len(active_listings)} active listings to re-process.")
    current_span.set_attribute("listings_to_reprocess", len(active_listings))

    for i, listing in enumerate(active_listings):
        logger.info(f"--- Re-processing listing {i+1}/{len(active_listings)} ---")
        # We set send_alert=True to ensure any new snipes are sent to Discord
        await process_listing(listing, queue, send_alert=True)
        await asyncio.sleep(1) # Be respectful to external APIs

    logger.info("--- Full re-check of all active listings complete! ---")

@tracer.start_as_current_span("initial_population")
async def initial_population(queue: asyncio.Queue):
    """
    Slowly fetches all ME listings, enriches them, and saves them to the DB.
    """
    logger.info("Database is empty. Starting full, slow population...")
    current_span = trace.get_current_span()
    
    all_listings, _ = await me.fetch_initial_listings_async()
    if not all_listings:
        logger.warning("Initial fetch returned no listings.")
        return
    
    current_span.set_attribute("listings_found", len(all_listings))
    logger.info(f"Found {len(all_listings)} total listings. Starting enrichment process...")
    
    for i, listing in enumerate(all_listings):
        with tracer.start_as_current_span("populate_one_listing") as loop_span:
            loop_span.set_attribute("listing.name", listing.get('name'))
            logger.info(f"--- Populating listing {i+1}/{len(all_listings)} ---")
            await asyncio.to_thread(database.save_listing, [listing])
            await process_listing(listing, queue, send_alert=False)
            await asyncio.sleep(1)
            
    logger.info("--- Initial population and enrichment complete! ---")

@tracer.start_as_current_span("watchdog_loop")
async def watchdog(queue: asyncio.Queue):
    """The main high-speed watchdog loop."""
    logger.info("--- Starting Watchdog ---")
    processed_ids = await asyncio.to_thread(database.get_all_listing_ids)
    logger.info(f"Loaded {len(processed_ids)} previously processed listing IDs.")
    
    while True:
        try:
            with tracer.start_as_current_span("watchdog_iteration") as iteration_span:
                new_listings = await me.fetch_new_listings_async(processed_ids)
                if new_listings:
                    iteration_span.set_attribute("new_listings_found", len(new_listings))
                    logger.info(f"Found {len(new_listings)} new items!")
                    
                    tasks = []
                    for listing in new_listings:
                        processed_ids.add(listing['listing_id'])
                        await asyncio.to_thread(database.save_listing, [listing])
                        tasks.append(process_listing(listing, queue, send_alert=True))
                    await asyncio.gather(*tasks)
                else:
                    iteration_span.set_attribute("new_listings_found", 0)

            await asyncio.sleep(0.3)
        except Exception as e:
            logger.critical(f"Unexpected error in watchdog loop: {e}", exc_info=True)
            trace.get_current_span().record_exception(e)
            trace.get_current_span().set_status(trace.Status(trace.StatusCode.ERROR))
            await asyncio.sleep(10)

async def main():
    """The main entry point for the application."""
    
    # --- Initialize Tracer ---
    # This must be done before any traced code is run
    tracing.init_tracer()
    
    snipe_queue = asyncio.Queue()
    logger.info("--- Sniper booting up ---")
    
    await asyncio.to_thread(database.init_db)

    initial_reaper_items = await asyncio.to_thread(database.get_initial_reaper_queue_items)
    for item in initial_reaper_items:
        await verification_queue.put(item)
    
    if not await asyncio.to_thread(database.get_all_listing_ids):
        await initial_population(snipe_queue)

    discord_task = asyncio.create_task(discord_bot.start_discord_bot(snipe_queue, lambda: recheck_all_listings(snipe_queue)))
    watchdog_task = asyncio.create_task(watchdog(snipe_queue))
    reaper_task = asyncio.create_task(reaper(verification_queue, snipe_queue))
    
    await asyncio.gather(discord_task, watchdog_task, reaper_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down sniper.")
