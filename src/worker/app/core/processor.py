import os
import logging
import time
import asyncio
from datetime import datetime, timezone, timedelta
from database import main as database
from worker.app.core import magic_eden as me
from worker.app.core import alt_data as alt
from worker.app.core import utils as utils
from worker.app.core import transactions
from worker.app.core import collector_crypt as cc

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
    # DEBUG: Confirm entry
    logger.warning(f"🔧 [Processor] Entering process_listing for {listing.get('name')}")
    
    skip_alt_fetch = False
    
    # --- 0. CACHE CHECK ---
    if 'last_analyzed_at' in listing and listing['last_analyzed_at'] is not None:
        try:
            last_analyzed_str = str(listing['last_analyzed_at']).replace('Z', '+00:00')
            last_analyzed_dt = datetime.fromisoformat(last_analyzed_str)
            if last_analyzed_dt.tzinfo is None:
                last_analyzed_dt = last_analyzed_dt.replace(tzinfo=timezone.utc)

            if (datetime.now(timezone.utc) - last_analyzed_dt).days < 1:
                # --- NOISE REDUCTION FIX ---
                # If we analyzed it recently, unless the price changed (handled by main.py check),
                # we should NOT re-log "Processing".
                # But main.py sends it if price changed > 0.001.
                # So if we are here, main.py thought it was new/changed.
                # BUT if we are here due to a restart/re-queue, we want to be quiet.
                
                # Check if it was a SKIP or Deal previously?
                # Ideally, we just trust the Cache and return.
                logger.info(f"ℹ️ [Cache Hit] Skipping logic for {listing.get('name')}") 
                return False, 'CACHE_HIT'
        except (ValueError, TypeError) as e:
            pass # Re-analyze on error

    start_time = time.time()
    
    # --- HELPER: Trace Logger ---
    async def log_trace(status_msg: str, details_override: dict = None):
         # Only log if the Trace Channel is configured
         if not os.getenv('LIVE_CARD_LOGS_CHANNEL_ID'):
             return
         if queue:
             await queue.put({
                 'listing_data': listing, 
                 'snipe_details': details_override or {}, 
                 'alert_level': 'TRACE', 
                 'reason': status_msg,
                 'duration': time.time() - start_time,
                 'broadcast_admins': False
             })


    # --- 0. DUPLICATE CHECK (Database) ---
    # prevent re-processing the same listing if price hasn't changed.
    # We do this AFTER the initial queue dump (trace) if you want to see it entering, 
    # BUT to save spam let's do it here.
    
    # Check if we have this listing ID already
    existing_db = await asyncio.to_thread(database.get_listing_by_id, listing.get('listing_id'))
    if existing_db:
         # Check price difference
         old_price = existing_db.get('price_amount') or 0.0
         new_price = listing.get('price_amount')
         if new_price and abs(new_price - old_price) < 0.0001:
             # Exactly the same price.
             # Check if we already have a decision (skipped, etc)
             # If it was skipped before, we still skip it.
             # If it was a deal, we might want to re-alert? No, that's annoying.
             # logger.info(f"⏭️ [Skipped] Duplicate: {listing.get('name')} (Price Unchanged)")
             return False, 'DUPLICATE'

    # --- 0.5 STRICT FILTERING (Safety Net) ---
    # User Requirement: Pokemon Cards Only + PSA/BGS Only.
    cat = listing.get('category', '').lower()
    comp = listing.get('grading_company', '').upper()
    
    # Trace: Initial Detection
    # await log_trace(f"Found {listing.get('name')} (Cat: {cat}, Comp: {comp})")

    if 'pokemon' not in cat:
         logger.warning(f"⚠️ [Skipped] Non-Pokemon Category: {cat} | {listing.get('name')}")
         await log_trace(f"❌ **Rejected (Filter)**: Category '{cat}' is not 'pokemon'.")
         return False, 'SKIP'
    if comp not in ['PSA', 'BGS', 'BECKETT']:
         logger.warning(f"⚠️ [Skipped] Invalid Company: {comp} | {listing.get('name')}")
         await log_trace(f"❌ **Rejected (Filter)**: Company '{comp}' is not PSA/BGS.")
         return False, 'SKIP'
    
    try:
        logger.warning(f"⚡ Processing: {listing.get('name')} | {listing.get('price_amount')} SOL")

        # --- 1.5. Truth Verification (Collector Crypt) ---
        # "Assert details... before we get fucked"
        # --- PARALLEL FETCHING (Speed Boost) ---
        # Fetch Checking Data (CC) and Valuation Data (Alt) at the same time.
        # This saves ~500-1000ms.
        
        cc_task = cc.fetch_cc_metadata(listing['token_mint'])
        
        if skip_alt_fetch:
            # Skip API, use Cache mock task
            async def mock_alt(): return {
                'alt_asset_id': listing.get('alt_asset_id'),
                'alt_name': listing.get('name'), # Basic assumption for cache
                'alt_value': listing.get('alt_value', 0),
                'avg_price': listing.get('avg_price', 0),
                'supply': listing.get('supply', 0),
                'lower_bound': listing.get('alt_value_lower_bound', 0),
                'upper_bound': listing.get('alt_value_upper_bound', 0),
                'confidence': listing.get('alt_value_confidence', 0)
            }
            alt_task = mock_alt()
        else:
             alt_task = alt.get_alt_data_async(
                    listing['grading_id'], 
                    listing.get('grade_num', 10),
                    listing['grading_company'],
                    fast_mode=fast_mode 
             )

        # Run both!
        logger.warning(f"⏳ [DEBUG] Starting Parallel Fetch (CC + Alt) for {listing.get('name')[:30]}...")
        cc_meta, processed_alt_data = await asyncio.gather(cc_task, alt_task)
        logger.warning(f"🏁 [DEBUG] Finished Parallel Fetch for {listing.get('name')[:30]}")

        # --- SEQUENTIAL VERIFICATION (Gated Logic) ---
        
        # Gate 1: Truth Verification (Collector Crypt)
        is_match, reason = cc.verify_match(listing, cc_meta)
        if not is_match:
            logger.warning(f"⚠️ [Skipped] Security Mismatch (CC): {reason} | {listing.get('name')}")
            return False, 'MISMATCH'
            
        logger.warning(f"✅ [Verified] Metadata matches CC: {listing.get('name')}")
        
        # Gate 2: Alt Triple Verification
        if not processed_alt_data:
            logger.warning(f"⚠️ [Skipped] No Alt Data Found: {listing.get('name')}")
            await log_trace(f"❌ **Rejected (Alt Data)**: No valuation found for '{listing.get('name')}'.")
            await asyncio.to_thread(database.skip_listing, listing['listing_id'], 'SKIP')
            return False, 'SKIP'
            
        # --- 1b. Triple Match Check (Name) ---
        alt_name = processed_alt_data.get('alt_name', 'Unknown')
        cc_name = cc_meta.get('title', '') if cc_meta else ''
        
        # Override Listing Name with Full CC Name for Storage/Display
        if cc_name:
             logger.warning(f"🔄 [Name Update] Replacing ME Name: '{listing.get('name')}' with CC Full Name: '{cc_name}'")
             listing['name'] = cc_name

        # --- Name Normalization / Triple Match DISABLED ---
        # User requested to rely on CC Verification (Gate 1) and proceed to Deal Logic.
        # We assume CC Name is the source of truth and have updated it above.
            


        # --- 2. Price Conversion ---
        logger.warning(f"💱 [DEBUG] Converting Price: {listing['price_amount']} {listing['price_currency']}")
        prices = await utils.get_price_in_both_currencies(listing['price_amount'], listing['price_currency'])
        if not prices: 
            logger.warning(f"⚠️ [Skipped] Price Conversion Failed: {listing.get('name')}")
            return False, 'SKIP'
        
        snipe_details = {**processed_alt_data, 'listing_price_usd': prices['price_usdc']}
        logger.warning(f"💰 [DEBUG] Alt Value: ${snipe_details.get('alt_value')} | Conf: {snipe_details.get('confidence')}")
        
        # --- 3. Determine Deal Status & Safety Checks ---
        alert_level = None
        alt_value = snipe_details.get('alt_value') or 0
        listing_price_usd = snipe_details.get('listing_price_usd') or 0
        alt_confidence = snipe_details.get('confidence') or 0
        cartel_category = 'SKIP'
        
        # KEYWORDS for Variant Checks
        # If Alt thinks it's a "Stamp" card (high value) but Listing Title doesn't say so -> DANGER
        # We check if Alt Value is suspicious (e.g. > 2x Price)
        security_flag = None
        if alt_value > (listing_price_usd * 2.0) and listing_price_usd > 0:
            title = listing.get('name', '').lower()
            risk_keywords = ['center', 'staff', 'prerelease', 'stamp', 'promo']
            # If Alt implies high value, we expect some indicator in title?
            # Actually, simpler: If Alt Value is huge, be PARANOID.
            # Eevee Case: Cost $130, Alt says $800.
            # We flag this discrepancy. 
            
            # Simple keyword match: If title lacks "center" but alt is priced like a "center" card? 
            # Hard to know what Alt thinks without scraping Alt page. 
            # BUT we know the User Rule: "Name for all 3 sites should be similar".
            # We already checked CC vs ME match.
            # Now checking Alt Reliability:
            # If Discount > 50%, we force a manual review unless we are 100% sure.
            
            # If Title missing 'center'/'stamp' but price gap is huge -> Undetermined.
            found_keyword = any(k in title for k in risk_keywords)
            if not found_keyword:
                 security_flag = "Potential Variant Mismatch (High Value, Low Price, No Keywords)"

        # DEBUG CHECK
        logger.warning(f"🧮 [DEBUG] Checking Deal Logic: Alt Val ${alt_value} | List USD ${listing_price_usd} | Conf {alt_confidence}")

        broadcast_admins = False
        target_discord_id = None

        if alt_value > 0 and listing_price_usd > 0:
            diff_percent = ((listing_price_usd - alt_value) / alt_value) * 100
            logger.warning(f"📉 Discount Calculated: {diff_percent:.2f}% (Price: ${listing_price_usd:.2f} vs Alt: ${alt_value:.2f})")
            
            # --- OPTIMIZATION: Early Exit if Overpriced ---
            if diff_percent > 0:
                logger.info(f"⚪ [Early Exit] Overpriced: {diff_percent:.2f}% > 0%. Skipping.")
                await log_trace(f"❌ **Rejected (Price)**: Overpriced by {diff_percent:.1f}%.", details_override=snipe_details)
                await asyncio.to_thread(database.update_listing_status, listing['listing_id'], is_listed=True, cartel_category='SKIP')
                return False, 'SKIP'

            # --- NOTIFICATION THRESHOLDS (TIER SYSTEM) ---
            
            # 1. HONEYPOT / SUSPICIOUS (>85% Discount)
            if diff_percent <= -85:
                # Almost certainly a fake listing or "photo of card" or "box only"
                logger.warning(f"⚠️ [SUSPICIOUS] {listing.get('name')} {diff_percent:.2f}% vs ${alt_value:.2f}")
                
                # Check Dedup for LOG
                is_known = await asyncio.to_thread(database.check_recent_notification, listing['listing_id'], 'LOG')
                if is_known:
                     logger.info(f"⚪ [Dedupe] Skipping SUSPICIOUS alert for {listing.get('name')}")
                     return False, 'Skipped'

                # Send to LOG channel so admins can verify if it was a missed snipe.
                msg = f"⚠️ **Suspicious / Risk**: {diff_percent:.1f}% Discount. (Price: ${listing_price_usd:.2f} vs Avg: ${alt_value:.2f}). Likely a scam/honeypot."
                if queue:
                    # System Log
                    await queue.put({
                        'listing_data': listing, 
                        'snipe_details': snipe_details, 
                        'alert_level': 'LOG', 
                        'reason': msg,
                        'duration': time.time() - start_time,
                        'broadcast_admins': False
                    })
                # Trace Log
                await log_trace(msg, details_override=snipe_details)
                return False, 'SUSPICIOUS'

            # 2. AUTOBUY / GOLD (>30% Discount)
            elif diff_percent <= -30: 
                # Variant Check
                if security_flag:
                    snipe_details['difference_str'] = f"⚠️ {diff_percent:+.2f}%"
                    alert_level = 'UNDETERMINED'
                    if queue:
                        await queue.put({
                            'listing_data': listing,
                            'snipe_details': snipe_details,
                            'alert_level': 'UNDETERMINED',
                            'reason': security_flag,
                            'duration': time.time() - start_time,
                            'broadcast_admins': True 
                        })
                    return False, 'RISK'
                
                # Confidence Check
                if alt_confidence > 75:
                    # AUTOBUY (Top Tier)
                    snipe_details['difference_str'] = f"🟢 {diff_percent:+.2f}%"
                    cartel_category = 'AUTOBUY'
                    alert_level = 'AUTOBUY'
                    # We DO NOT set broadcast_admins here yet, because we might buy it.
                    # Logic is handled in Step 4.
                else:
                    # GOLD (High Value, Lower Confidence)
                    snipe_details['difference_str'] = f"⚠️ {diff_percent:+.2f}%"
                    alert_level = 'GOLD'
                    cartel_category = 'GOLD' # ALERT ONLY
                    logger.warning(f"📉 Downgrading AUTOBUY to GOLD due to confidence {alt_confidence} <= 75")
                    broadcast_admins = True
            
            # 3. RED / HIGH (>20% Discount)
            elif diff_percent <= -20: 
                snipe_details['difference_str'] = f"{diff_percent:+.2f}%"
                alert_level = 'HIGH' # Red
                cartel_category = 'GOOD'
                broadcast_admins = True

            # 4. BLUE / INFO (>15% Discount)
            elif diff_percent <= -15: 
                snipe_details['difference_str'] = f"{diff_percent:+.2f}%"
                alert_level = 'INFO' # Blue
                cartel_category = 'OK'
                logger.info(f"🔵 [Info Alert] {diff_percent:.2f}% Discount")
                broadcast_admins = False
            
            else:
                logger.info(f"⚪ [Ignore] Discount {diff_percent:.2f}% is < 15%")

        # --- 4. PRIORITY EXECUTION (The "Shotgun") ---
    
        # Trace Final Outcome
        status_msg = f"✅ **Processed**: Price ${listing_price_usd:.2f} vs Avg ${alt_value:.2f} ({diff_percent:+.1f}%)"
        if alert_level:
             status_msg += f" -> **Alert: {alert_level}**"
        else:
             status_msg += " -> **No Deal** (Price too high)"
        await log_trace(status_msg, details_override=snipe_details)

        # Critical: Verify logic runs only for AUTOBUY deals
        if cartel_category == 'AUTOBUY':
            t_buy_start = time.time()
            
            # Fetch Buyers
            eligible_buyers = await asyncio.to_thread(database.get_eligible_buyers, listing['price_amount'])
            
            if eligible_buyers:
                logger.info(f"⚡ AUTOBUY TRIGGERED for {listing.get('name')}! Found {len(eligible_buyers)} buyers.")
                
                # Iterate by Priority (Eligible buyers already sorted by priority in DB query)
                for buyer in eligible_buyers:
                    user_wallet = buyer.get('user_wallet')
                    priority = buyer.get('priority')
                    
                    logger.info(f"  -> Attempting Buy for User: {user_wallet} (Priority {priority})")
                    

                    
                    # Execute Buy Transaction
                    success = await transactions.execute_buy(
                        user_wallet=user_wallet,
                        encrypted_private_key=buyer.get('encrypted_private_key'),
                        listing=listing,
                        rpc_endpoint=buyer.get('rpc_endpoint')
                    )
                    
                    if success:
                        logger.info(f"✅ AUTOBUY SUCCESS for User: {user_wallet}!")
                        
                        # --- 1. Save Notification to DB ---
                        msg_title = f"Autobuy Success: {listing.get('name')}"
                        msg_body = f"Purchased for {listing.get('price_amount')} {listing.get('price_currency')}."
                        await asyncio.to_thread(
                            database.create_notification,
                            user_wallet=user_wallet,
                            title=msg_title,
                            message=msg_body,
                            type='AUTOBUY',
                            params=listing
                        )

                        # --- 2. Queue DM Notification (Use DB Discord ID) ---
                        discord_id = buyer.get('discord_id')
                        # For AUTOBUY: We ALWAYS broadcast to Admins too, so they know the bot is working.
                        if queue:
                             await queue.put({
                                'listing_data': listing, 
                                'snipe_details': snipe_details, 
                                'alert_level': 'AUTOBUY', # Signal to Bot: Buy Executed
                                'target_discord_id': discord_id, # DM the Buyer
                                'broadcast_admins': True, # Keep Admins in loop
                                'duration': time.time() - start_time
                            })

                        pass # Continue so others have a chance (or break if strict) 
                    
            logger.debug(f"Buy check execution took: {time.time() - t_buy_start:.3f}s")
            
            # If we bought it, we don't need the general alert below, as we keyed 'AUTOBUY' alert above.
            # But if we FAILED to buy (no liquidity/error), we should fall back to a GOLD alert?
            # Ideally yes. But for now complexity wise, if we attempted buy, we triggered 'AUTOBUY' alert above.
            # If no buyers found? We fall through to general alert.
            if eligible_buyers:
                # If we had buyers, we likely sent alerts inside the loop or failed.
                # If we failed all buys, we might want to alert admins "Failed Buy".
                # For now, let's let the flow continue.
                pass

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
            # Queue Alert
            if send_alert and queue and alert_level:
                # --- Deduplication Check ---
                is_known = await asyncio.to_thread(
                    database.check_recent_notification, 
                    listing['listing_id'], 
                    alert_level
                )
                
                if is_known:
                     logger.info(f"⚪ [Dedupe] Skipping {alert_level} alert for {listing.get('name')} (Recently sent)")
                else:
                    await queue.put({
                        'listing_data': listing, 
                        'snipe_details': snipe_details, 
                        'alert_level': alert_level,
                        'duration': time.time() - start_time,
                        'broadcast_admins': broadcast_admins
                    })
            found_deal = True
       
        # Update DB
        await asyncio.to_thread(database.update_listing, listing['listing_id'], snipe_details, cartel_category, name=listing.get('name'))
        
        if not found_deal:
             logger.warning(f"🏁 [DEBUG] Processor Finished: NO DEAL for {listing.get('name')[:30]}...")

        elapsed = time.time() - start_time
        perf_icon = "🚀" if elapsed < 0.5 else "🐢"
        logger.info(f"{perf_icon} [PERF] Decision Time: {elapsed:.3f}s | Deal: {cartel_category} | {listing.get('name')[:30]}")

        return found_deal, cartel_category

    except Exception as e:
        logger.error(f"❌ [Error] Processor Exception: {e}", exc_info=True)
        return False, 'ERROR'
