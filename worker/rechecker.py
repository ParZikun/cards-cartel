
import logging
from datetime import datetime, timedelta
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database
import get_magic_eden_data

logger = logging.getLogger(__name__)

async def recheck_listings():
    """
    Re-checks active listings older than 24 hours to verify their status.
    """
    logger.info("Starting automated re-checking service for stale listings...")
    
    active_listings = database.get_all_active_listings()
    now = datetime.utcnow()
    
    for listing in active_listings:
        listed_at = datetime.fromisoformat(listing['listed_at'].replace('Z', '+00:00'))
        
        if now - listed_at > timedelta(hours=24):
            logger.info(f"Re-checking listing: {listing['listing_id']}")
            status = await get_magic_eden_data.check_listing_status_async(listing['token_mint'])
            
            if status != 'listed':
                logger.info(f"Listing {listing['listing_id']} is no longer active. Updating status to unlisted.")
                database.update_listing_status(listing['token_mint'], is_listed=False)

def start_rechecker():
    """
    Starts the scheduler for the re-checking service.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(recheck_listings, 'interval', hours=1)
    scheduler.start()
    logger.info("Automated re-checking service scheduled to run every hour.")
