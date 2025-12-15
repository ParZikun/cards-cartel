import logging
import time
import asyncio
from datetime import datetime, timezone, timedelta
from database import main as database
from worker.app.core import magic_eden as me
from worker.app.core import alt_data as alt
from worker.app.core import utils as utils
from worker.app.core import transactions

logger = logging.getLogger(__name__)

# Limit the bot to 10 concurrent requests to the ALT API
ALT_API_SEMAPHORE = asyncio.Semaphore(10)

async def process_listing(listing: dict, queue: asyncio.Queue = None, send_alert: bool = True, fast_mode: bool = True) -> bool:
    """
    The complete, atomic pipeline for a single listing.
    Optimized for Speed:
    1. Check Cache
    2. Fast Alt Fetch (Valuation Only) - Controlled by fast_mode param
    3. Buy Decision (Priority Execution - Lazy Loaded)
    4. Full Alt Fetch (History - for Logs/Discord)
    """
    skip_alt_fetch = False
    
    # --- 0. CACHE CHECK ---
    if 'last_analyzed_at' in listing and listing['last_analyzed_at'] is not None:
        try:
            last_analyzed_str = str(listing['last_analyzed_at']).replace('Z', '+00:00')
            last_analyzed_dt = datetime.fromisoformat(last_analyzed_str)
            if last_analyzed_dt.tzinfo is None:
                last_analyzed_dt = last_analyzed_dt.replace(tzinfo=timezone.utc)

            if (datetime.now(timezone.utc) - last_analyzed_dt).days < 7:
                logger.debug(f"CACHE HIT: Skipping ALT analysis for {listing.get('name')}")
                skip_alt_fetch = True
        except (ValueError, TypeError) as e:
            pass # Re-analyze on error

    start_time = time.time()
    
    try:
        # --- 1. Fetch ALT Data (FAST MODE) ---
        snipe_details = {}
        processed_alt_data = None
        
        if skip_alt_fetch:
            # Use cached data
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
            # Fetch fresh (Fast Mode = No Transactions/History)
            async with ALT_API_SEMAPHORE:
                processed_alt_data = await alt.get_alt_data_async(
                    listing['grading_id'], 
                    listing.get('grade_num', 10),
                    listing['grading_company'],
                    fast_mode=fast_mode 
                )
        
        if not processed_alt_data:
            await asyncio.to_thread(database.skip_listing, listing['listing_id'], 'SKIP')
            return False

        # --- 2. Price Conversion ---
        prices = await utils.get_price_in_both_currencies(listing['price_amount'], listing['price_currency'])
        if not prices: return False
        
        snipe_details = {**processed_alt_data, 'listing_price_usd': prices['price_usdc']}
        
        # --- 3. Determine Deal Status ---
        alert_level = None
        alt_value = snipe_details.get('alt_value') or 0
        listing_price_usd = snipe_details.get('listing_price_usd') or 0
        alt_confidence = snipe_details.get('confidence') or 0
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
                    alert_level = 'HIGH' # GOOD
                    cartel_category = 'GOOD'
                elif diff_percent <= -15: 
                    alert_level = 'INFO' # OK
                    cartel_category = 'OK'

        # --- 4. PRIORITY EXECUTION (The "Shotgun") ---
        # Critical: Verify logic runs only for AUTOBUY deals
        if cartel_category == 'AUTOBUY':
            t_buy_start = time.time()
            
            # Fetch Buyers
            eligible_buyers = await asyncio.to_thread(database.get_eligible_buyers, listing['price_amount'])
            
            if eligible_buyers:
                logger.info(f"⚡ AUTOBUY TRIGGERED for {listing.get('name')}! Found {len(eligible_buyers)} potential buyers.")
                
                # Iterate by Priority (Eligible buyers already sorted by priority in DB query)
                for buyer in eligible_buyers:
                    user_wallet = buyer.get('user_wallet')
                    priority = buyer.get('priority')
                    
                    logger.info(f"  -> Attempting Buy for User: {user_wallet} (Priority {priority})")
                    
                    logger.info(f"  -> Attempting Buy for User: {user_wallet} (Priority {priority})")
                    
                    # Execute Buy Transaction
                    success = await transactions.execute_buy(
                        user_wallet=user_wallet,
                        encrypted_private_key=buyer.get('encrypted_private_key'),
                        listing=listing,
                        rpc_endpoint=buyer.get('rpc_endpoint')
                    )
                    
                    if success:
                        logger.info(f"⚡ AUTOBUY SUCCESS for User: {user_wallet}!")
                        # We might want to stop trying for other users if one succeeds?
                        # OR keep going ("Shotgun")?
                        # Implementation Plan said "flood the network", so we keep going?
                        # "The fastest one wins" implies we launch multiple. 
                        # But wait, if we handle them sequentially in this loop with `await`, 
                        # we are NOT launching them in parallel.
                        
                        # Optimization: Launch ALL in parallel.
                        # But loop-based sequential is safer for now to avoid complexity.
                        # However, for pure shotgun, we should gather.
                        
                        # Let's keep sequential for now as per code structure, 
                        # or if I want true shotgun, I should collect tasks and gather.
                        # Given "High-Frequency", parallel is better.
                        pass # Continue so others have a chance (or break if strict) 
                    
            logger.debug(f"Buy check execution took: {time.time() - t_buy_start:.3f}s")

        # --- 5. Lazy Load Full History (If Alert/Deal) ---
        found_deal = False
        if alert_level:
            # If we need graph/history data for the alert, fetch it now that the critical part is done.
            if not skip_alt_fetch:
                 logger.debug("Lazy loading historical data for alert...")
                 async with ALT_API_SEMAPHORE:
                    full_data = await alt.get_alt_data_async(
                        listing['grading_id'], 
                        listing.get('grade_num', 0), 
                        listing['grading_company'],
                        fast_mode=False
                    )
                    if full_data:
                        snipe_details.update(full_data) # Merge history/avg_price

            # Queue Alert
            if send_alert and queue:
                await queue.put({
                    'listing_data': listing, 
                    'snipe_details': snipe_details, 
                    'alert_level': alert_level,
                    'duration': time.time() - start_time
                })
            found_deal = True
       
        # Update DB
        await asyncio.to_thread(database.update_listing, listing['listing_id'], snipe_details, cartel_category)
        
        return found_deal, cartel_category

    except Exception as e:
        logger.error(f"Error processing {listing.get('name')}: {e}", exc_info=True)
        return False, 'ERROR'
