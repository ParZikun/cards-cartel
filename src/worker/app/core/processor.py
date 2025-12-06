import logging
import time
import asyncio
from datetime import datetime, timezone, timedelta
from database import main as database
from worker.app.core import magic_eden as me
from worker.app.core import alt_data as alt
from worker.app.core import utils as utils

logger = logging.getLogger(__name__)

# Limit the bot to 10 concurrent requests to the ALT API
# We redefine this here or import it if it was shared. 
# For now, let's keep it local to the module to avoid circular deps if main imports this.
ALT_API_SEMAPHORE = asyncio.Semaphore(10)

async def process_listing(listing: dict, queue: asyncio.Queue = None, send_alert: bool = True) -> bool:
    """
    The complete, atomic pipeline for a single listing.
    Returns True if a new deal was found, False otherwise.
    
    Args:
        listing: The listing dictionary from the database/ME.
        queue: Optional asyncio.Queue to put alerts into (for Discord bot).
        send_alert: Whether to generate alerts.
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
        if alert_level and send_alert and queue:
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
        
        # Return the logic for verification_queue handling to the caller?
        # Ideally, this function should just process. The caller handles side effects like queuing for reaper.
        # But `process_listing` was adding to `verification_queue` (now separate from `queue` arg which is `snipe_queue`).
        # To keep it pure, we might want to return the result and let caller handle reaper queue.
        # However, to minimize refactor risk, let's keep it but we need access to `verification_queue`.
        # Since `verification_queue` is global in main.py, we should pass it as an arg if needed.
        # For now, let's just return the necessary info or handle it if passed.
        
        # NOTE: The original code pushed to `verification_queue`. 
        # We will return the category/mint so the caller can push to verification_queue.
        
        total_duration = time.time() - start_time
        if alert_level:
             logger.info(f"Successfully processed {listing.get('name')}. Took {total_duration:.3f}s. Alert: {alert_level}")
        else:
             logger.debug(f"Processed {listing.get('name')} (No Alert). Took {total_duration:.3f}s.")
             
        return found_deal, cartel_category

    except Exception as e:
        logger.error(f"Unexpected error while processing {listing.get('name')}: {e}", exc_info=True)
        return False, 'ERROR'
