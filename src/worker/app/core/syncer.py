import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

# Adjust path to ensure imports work if run as script (less relevant now as module)
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# if PROJECT_ROOT not in sys.path:
#    sys.path.insert(0, PROJECT_ROOT)

from database import main as database
from worker.app.core import magic_eden as me
from worker.app.core import processor

logger = logging.getLogger(__name__)

async def full_sync(queue: asyncio.Queue = None):
    """
    Main function to sync the database with Magic Eden, check for deals, and update listings.
    """
    logger.info("--- Starting full sync with Magic Eden ---")

    # 1. Fetch all listings from Magic Eden
    me_listings = await me.fetch_all_listings_paginated_async()
    me_listings_map = {listing['token_mint']: listing for listing in me_listings}
    logger.info(f"Fetched {len(me_listings_map)} unique listings from Magic Eden.")

    # 2. Fetch all active listings from the database
    db_listings = await asyncio.to_thread(database.get_all_active_listings)
    db_listings_map = {listing['token_mint']: listing for listing in db_listings}
    logger.info(f"Found {len(db_listings_map)} active listings in the database.")

    # 3. Identify delisted items
    delisted_mints = set(db_listings_map.keys()) - set(me_listings_map.keys())
    logger.info(f"Found {len(delisted_mints)} listings to mark as delisted.")
    for mint in delisted_mints:
        await asyncio.to_thread(database.update_listing_status, mint, is_listed=False)

    # 4. Process new and existing listings
    new_deals_count = 0
    for i, (mint, me_listing) in enumerate(me_listings_map.items()):
        # logger.info(f"--- ({i+1}/{len(me_listings_map)}) Processing mint: {mint} ---")
        db_listing = db_listings_map.get(mint)

        if not db_listing:
            # New listing
            logger.info(f"New listing found: {me_listing['name']}. Saving to database.")
            await asyncio.to_thread(database.save_listing, [me_listing])
            # The listing is now in the DB, so we can analyze it.
            new_db_listing = await asyncio.to_thread(database.get_listing_by_mint, mint)
            if new_db_listing:
                found, _ = await processor.process_listing(new_db_listing, queue)
                if found: new_deals_count += 1
            else:
                logger.error(f"Could not retrieve new listing {mint} from DB after saving.")
        else:
            # Existing listing
            # Check if it was analyzed recently (< 24h)
            last_analyzed = db_listing.get('last_analyzed_at')
            if last_analyzed:
                if isinstance(last_analyzed, str):
                    last_analyzed = datetime.fromisoformat(last_analyzed.replace('Z', '+00:00'))
                if last_analyzed.tzinfo is None:
                    last_analyzed = last_analyzed.replace(tzinfo=timezone.utc)
                
                # User Optimization: Skip if updated < 24h ago
                if datetime.now(timezone.utc) - last_analyzed < timedelta(hours=24):
                    logger.debug(f"Skipping {mint} (Analyzed recently: {last_analyzed})")
                    continue
            
            # If stale, re-analyze
            # logger.info(f"Existing listing found: {me_listing['name']}. Re-analyzing.")
            db_listing['price_amount'] = me_listing['price_amount']
            found, _ = await processor.process_listing(db_listing, queue)
            if found: new_deals_count += 1
            
        # Small sleep to yield control
        if i % 10 == 0:
            await asyncio.sleep(0.01)

    logger.info(f"--- Full database sync complete! Found {new_deals_count} new deals. ---")
    return new_deals_count

async def recheck_listings(duration_str: str, queue: asyncio.Queue = None):
    """
    Fetches active listings marked as 'SKIP' within a given timeframe and re-processes them.
    Duration string: "1H", "24H", "1D", etc.
    """
    logger.info(f"--- Starting a re-check of 'SKIP' listings for timeframe: {duration_str} ---")
    
    time_deltas = {
        "1H": timedelta(hours=1),
        "2H": timedelta(hours=2),
        "6H": timedelta(hours=6),
        "12H": timedelta(hours=12),
        "24H": timedelta(hours=24),
        "1D": timedelta(days=1),
        "1W": timedelta(weeks=1),
        "1M": timedelta(days=30),
        "ALL": None
    }
    
    # Simple parser if not in map
    delta = time_deltas.get(duration_str.upper())
    
    if not delta and duration_str.upper() != "ALL":
         # Try to parse generic e.g. "5H"
         try:
             import re
             match = re.match(r"(\d+)([DHWM])", duration_str.upper())
             if match:
                 val, unit = match.groups()
                 val = int(val)
                 if unit == 'D': delta = timedelta(days=val)
                 elif unit == 'H': delta = timedelta(hours=val)
                 elif unit == 'W': delta = timedelta(weeks=val)
                 elif unit == 'M': delta = timedelta(days=val*30)
         except:
             pass

    since_timestamp = None
    if delta:
        since_timestamp = datetime.now(timezone.utc) - delta
    elif duration_str.upper() != "ALL":
        logger.warning(f"Unknown duration {duration_str}, defaulting to 1 Hour.")
        since_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)

    skipped_listings = await asyncio.to_thread(database.get_skipped_listings, since_timestamp)

    if not skipped_listings:
        logger.warning(f"Re-check initiated for {duration_str}, but no 'SKIP' listings found in that period.")
        return 0

    logger.info(f"Found {len(skipped_listings)} 'SKIP' listings to re-process.")
    
    # Define freshness thresholds (User requested ~25% of duration)
    # If list was updated more recently than this, skip it.
    freshness_map = {
        "1H": timedelta(minutes=15),
        "2H": timedelta(minutes=30),
        "6H": timedelta(hours=1, minutes=30),
        "12H": timedelta(hours=3),
        "24H": timedelta(hours=6),
        "1D": timedelta(hours=6),
        "1W": timedelta(days=1),   # ~15% but reasonable
        "1M": timedelta(days=5),
        "ALL": timedelta(days=1)   # Default for ALL is 24h
    }
    freshness_threshold = freshness_map.get(duration_str.upper(), timedelta(minutes=15)) # Default to 15m
    
    new_deals_count = 0
    for i, listing in enumerate(skipped_listings):
        # Freshness Check
        last_analyzed = listing.get('last_analyzed_at')
        if last_analyzed:
            if isinstance(last_analyzed, str):
                last_analyzed = datetime.fromisoformat(last_analyzed.replace('Z', '+00:00'))
            if last_analyzed.tzinfo is None:
                last_analyzed = last_analyzed.replace(tzinfo=timezone.utc)
            
            if datetime.now(timezone.utc) - last_analyzed < freshness_threshold:
                logger.debug(f"Skipping Recheck for {listing.get('token_mint')} (Analyzed recently: {last_analyzed})")
                continue

        # logger.info(f"--- Re-processing listing {i+1}/{len(skipped_listings)} ---")
        found, _ = await processor.process_listing(listing, queue, send_alert=True)
        if found:
            new_deals_count += 1
        await asyncio.sleep(0.55)

    logger.info(f"--- Re-check for timeframe '{duration_str}' complete! Found {new_deals_count} new deals. ---")
    return new_deals_count
