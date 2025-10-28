import os
from dotenv import load_dotenv

# --- Centralized Environment Loading ---
# Load .env.local for local development, otherwise fall back to .env
if os.path.exists('.env.local'):
    print("Loading configuration from .env.local for local testing.")
    load_dotenv(dotenv_path='.env.local')
else:
    load_dotenv()

import time
import asyncio
import yaml
import logging
import logging.config
import database

# --- Tracing Imports ---
from opentelemetry import trace
import tracing

# Import the new async functions
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

# --- Setup Tracing ---
# This will be used to create spans
tracer = tracing.get_tracer(__name__)

verification_queue = asyncio.Queue()

async def reaper(queue: asyncio.Queue):
    """Pulls a mint address from the queue, verifies its status, and acts on it."""
    logger.info("--- Starting Reaper ---")
    while True:
        mint_address = None
        try:
            # Start a new span for each item pulled from the queue
            with tracer.start_as_current_span("reaper_iteration") as iteration_span:
                mint_address = await queue.get()
                iteration_span.set_attribute("mint_address", mint_address)
                
                status = await me.check_listing_status_async(mint_address)
                iteration_span.set_attribute("listing.status", status)

                if status == "listed":
                    await queue.put(mint_address)
                else:
                    logger.info(f"Reaper: Listing {mint_address} is no longer active (status: {status}). Updating DB.")
                    await asyncio.to_thread(database.update_listing_status, mint_address, False)

                await asyncio.sleep(0.55)
        except Exception as e:
            logger.error(f"Error in reaper task: {e}", exc_info=True)
            # Ensure the span is recorded in case of an error
            if 'iteration_span' in locals():
                iteration_span.record_exception(e)
                iteration_span.set_status(trace.Status(trace.StatusCode.ERROR))
        finally:
            # Only call task_done if an item was actually retrieved from the queue
            if mint_address is not None:
                queue.task_done()

@tracer.start_as_current_span("process_listing")
async def process_listing(listing: dict, queue: asyncio.Queue, send_alert: bool = True):
    """
    The complete, atomic pipeline for a single listing.
    """
    start_time = time.time()
    logger.info(f"Processing: {listing.get('name')} ({listing.get('grading_id')})")
    
    current_span = trace.get_current_span()
    # Add key details to the span to make it searchable
    current_span.set_attribute("listing.id", listing.get('listing_id'))
    current_span.set_attribute("listing.name", listing.get('name'))
    current_span.set_attribute("listing.grade_id", listing.get('grading_id'))

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

        prices = await asyncio.to_thread(utils.get_price_in_both_currencies, listing['price_amount'], listing['price_currency'])
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

    discord_task = asyncio.create_task(discord_bot.start_discord_bot(snipe_queue))
    watchdog_task = asyncio.create_task(watchdog(snipe_queue))
    reaper_task = asyncio.create_task(reaper(verification_queue))
    
    await asyncio.gather(discord_task, watchdog_task, reaper_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down sniper.")
