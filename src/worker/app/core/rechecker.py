
import logging
from datetime import datetime, timedelta, timezone
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import main as database
from worker.app.core import magic_eden as me

logger = logging.getLogger(__name__)

async def recheck_listings():
    """
    Re-checks active listings to verify their status if they haven't been checked in the last 24 hours.
    """
    logger.info("Starting automated re-checking service for stale listings...")
    
    active_listings = await asyncio.to_thread(database.get_all_active_listings)
    now = datetime.now(timezone.utc)
    
    for listing in active_listings:
        last_analyzed_str = listing.get('last_analyzed_at')
        
        if not last_analyzed_str:
            logger.debug(f"Skipping listing {listing.get('listing_id')} because last_analyzed_at is missing.")
            continue

        try:
            # Assuming the timestamp from the DB is a string like 'YYYY-MM-DD HH:MM:SS' and is in UTC
            last_analyzed_at = datetime.strptime(last_analyzed_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse last_analyzed_at: '{last_analyzed_str}' for listing {listing.get('listing_id')}. Skipping.")
            continue
            
        age = now - last_analyzed_at
        logger.info(f"Listing {listing.get('listing_id')} was last analyzed {age} ago.")

        if age > timedelta(hours=24):
            logger.info(f"Re-checking listing: {listing['listing_id']} (last checked {age} ago).")
            status = await me.check_listing_status_async(listing['token_mint'])
            
            if status == 'not_found':
                logger.info(f"Listing {listing['listing_id']} is no longer active. Updating status to unlisted.")
                await asyncio.to_thread(database.update_listing_status, listing['token_mint'], is_listed=False)
        else:
            logger.info(f"Skipping re-check for listing {listing['listing_id']} as it was checked within 24 hours.")


def start_rechecker():
    """
    Starts the scheduler for the re-checking service.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(recheck_listings, 'interval', hours=1)
    scheduler.start()
    logger.info("Automated re-checking service scheduled to run every hour.")
