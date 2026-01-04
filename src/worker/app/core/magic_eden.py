import httpx
import json
import asyncio
import logging
import time # Perf Logging
import re
import os
from dotenv import load_dotenv

# Ensure env vars are loaded
if os.path.exists('.env.local'):
    load_dotenv(dotenv_path='.env.local')
else:
    load_dotenv()

# Initialize a logger for this module
logger = logging.getLogger(__name__)

# Default fallback if not passed (though we aim to pass it)
DEFAULT_BLACKLIST = ['black star', 'sticker', 'stickers']

# Standard headers to mimic browser behavior and avoid 403s
# Standard headers to mimic browser behavior and avoid 403s
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

HEADERS = BASE_HEADERS.copy()

# Inject API Key if present
api_key = os.getenv("ME_API_KEY")
if api_key:
    HEADERS["Authorization"] = f"Bearer {api_key}"
    logger.info("Using Magic Eden API Key for authenticated requests.")
else:
    logger.warning("No Magic Eden API Key found. Rate limits will be strict.")

# Authenticated Client (For V2 API)
async_client = httpx.AsyncClient(headers=HEADERS, timeout=20)

# Public Client (For Idxv2 API - No Auth to avoid issues)
public_async_client = httpx.AsyncClient(headers=BASE_HEADERS, timeout=20)

# Semaphore to prevent burst 429s (Limit to 2 concurrent checks)
STATUS_CHECK_SEMAPHORE = asyncio.Semaphore(2)

# Global Deduplication Manager
class ProcessingManager:
    def __init__(self):
        self._processing_mints = set() # Active Locks
        self._processed_cache = {} # Mint -> {price, time}
        self.lock = asyncio.Lock()
    
    async def try_acquire(self, mint, price):
        async with self.lock:
            # 1. Check Active Lock
            if mint in self._processing_mints:
                return False, "LOCKED"
            
            # 2. Check Cache
            cached = self._processed_cache.get(mint)
            if cached and abs(cached['price'] - price) < 0.001:
                # Same price = Duplicate
                return False, "CACHE_HIT"
            
            # Acquire
            self._processing_mints.add(mint)
            return True, None

    async def release(self, mint, price=None):
        async with self.lock:
            if mint in self._processing_mints:
                self._processing_mints.remove(mint)
            if price is not None:
                self._processed_cache[mint] = {'price': price, 'time': time.time()}

PROCESSING_MANAGER = ProcessingManager()

# Watchlist for Debugging Missing Snipes
DEBUG_MINTS = [
    "EEpashtrTXY9xTWgN27BH5GxUYnhCDH44qWj2EZ8pRZL" # Full Art/Cynthia
]

def _get_attribute_value(attributes_list: list, target_trait: str):
    """Finds the value for a specific traitType within a list of attributes."""
    if not attributes_list: return None
    for attribute in attributes_list:
        if attribute.get('trait_type') == target_trait:
            return attribute.get('value')
    return None

def _process_listing(listing: dict, blacklisted_keywords: list[str] = None):
    # ... (rest of _process_listing is unchanged, assuming it's correct in context)
    pass # Replaced content below handles the function body correctly by NOT including it if I don't target it.
    # Wait, replace_file_content replaces the BLOCK. I need to be careful not to delete _process_listing.
    # I should only replace the top imports and the candidate fetching loop.
    # I will split this into two edits if needed, or use a larger block and include existing code.
    # Actually, I can just replace the imports and GLOBAL vars at the top.
    
# ... (I'll stick to the actual tool call parameters)

# EDIT 1: Imports and Globals
# EDIT 2: fetch_new_listings_async logic

# Let's do EDIT 2 (The throttle) first as it's deeper in the file.
# Wait, let's do EDIT 1 first to get load_dotenv.

# Re-evaluating: I can do it in one go if I am careful, but safer to do two small edits.

# Edit 1: Top of file imports and checking


def _get_attribute_value(attributes_list: list, target_trait: str):
    """Finds the value for a specific traitType within a list of attributes."""
    if not attributes_list: return None
    for attribute in attributes_list:
        if attribute.get('trait_type') == target_trait:
            return attribute.get('value')
    return None

def _process_listing(listing: dict, blacklisted_keywords: list[str] = None):
    """
    Processes a single raw listing from the /idxv2/ API.
    Returns the processed dictionary or None if it's invalid.
    """
    if not listing: return None

    # CRITICAL FIX: Ensure listing_id exists.
    listing_id = listing.get('id') or listing.get('mintAddress') or listing.get('tokenMint')
    if not listing_id:
        # If we absolutely cannot find an ID, we cannot process this.
        return None

    # CRITICAL: Idxv2 uses 'content', Activity/V2 uses 'name' or 'title'
    name = listing.get('content') or listing.get('name') or listing.get('title') or "Unknown"

    # CRITICAL: If no price, it's likely unlisted or not a valid listing object.
    raw_price = listing.get('price')
    price_info = listing.get('priceInfo') # Sometimes nested
    
    if not raw_price and not price_info:
        # Silently skip items that are clearly not listed
        # (The activity feed often returns "list" events that reference a mint, but the fetched details might be stale or partial)
        return None

    # DEBUG: Raw Data Dump only if name is missing (Price is handled above)
    if name == "Unknown":
         # Limit log size
         logger.warning(f"🚨 [Mapping Fail] Name Unknown: {json.dumps(listing, default=str)[:1000]}")
    
    # Use passed list or default
    blacklist = blacklisted_keywords if blacklisted_keywords is not None else DEFAULT_BLACKLIST
    
    for keyword in blacklist:
        if keyword in name.lower():
            logger.info(f"⚠️ [Skipped] Blacklisted: {name} (Keyword: {keyword})")
            return None

    attributes = listing.get('attributes', [])
    # --- STRICT FILTERING (User Request) ---
    # 1. Verification: Category MUST be Pokemon
    category_attr = _get_attribute_value(attributes, "Category")
    if not category_attr or "pokemon" not in category_attr.lower():
        # logger.debug(f"⚠️ [Skipped] Non-Pokemon Category: {category_attr} for {name}")
        return None

    # 2. Verification: Company MUST be PSA, BGS, or Beckett
    company = _get_attribute_value(attributes, "Grading Company")
    if not company:
        return None
        
    company_upper = company.upper()
    if company_upper not in ["PSA", "BECKETT", "BGS"]:
        # logger.debug(f"⚠️ [Skipped] Invalid Company: {company} for {name}")
        return None
        
    if company_upper in ["BECKETT", "BGS"]: 
        company = "BGS"
    else:
        company = "PSA" 

    # 3. Simplify Internal Category (Legacy logic, but kept for DB consistency)
    category = "Pokemon Card"
    if name and "Bundle" in name:
        category = "Bundle"
    elif name and "Box" in name:
        category = "Box"

    grade = _get_attribute_value(attributes, "The Grade")
    cert_id = _get_attribute_value(attributes, "Grading ID")
    grade_num_str = _get_attribute_value(attributes, "GradeNum")
    insured_value_str = _get_attribute_value(attributes, "Insured Value")
    
    try:
        grade_num = float(grade_num_str) if grade_num_str is not None else 0.0
        
        # --- Grade Verification from Attribute String ---
        # "The Grade" attribute often contains the number mixed with text (e.g. "9-Mint", "GEM-MT 10").
        # We extract the number from this string to ensure accuracy.
        if grade:
            grade_match = re.search(r"(\d+(?:\.\d+)?)", str(grade))
            if grade_match:
                try:
                    grade_from_str = float(grade_match.group(1))
                    if grade_from_str != grade_num:
                        logger.debug(f"Grade mismatch for {name}: Attr String '{grade}' says {grade_from_str}, GradeNum says {grade_num}. Using String.")
                        grade_num = grade_from_str
                        # Update the grade variable to be the number, as that's what we usually want for logic
                        grade = str(grade_from_str)
                except ValueError:
                    pass
        # ------------------------------------
        insured_value = float(insured_value_str) if insured_value_str is not None else 0.0
        price_sol = float(listing.get('price', 0))
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ [Skipped] Data Error for '{name}': {e}")
        return None

    if not all([cert_id, name, grade, company]):
        logger.info(f"⚠️ [Skipped] Missing Attributes: {name} (Cert={cert_id}, Grade={grade}, Company={company})")
        return None
    
    price_sol = float(listing.get('price', 0))
    
    # Currency Detection
    price_currency = 'SOL'
    sol_price_data = listing.get('solPrice', {})
    if sol_price_data.get('address') == 'EPjfwdd5SrqNsFC8CVU4FzJ8G8FpTE3j3v24g85r8rV':
        price_currency = 'USDC'

    if price_sol <= 0: 
        logger.info(f"⚠️ [Skipped] Zero Price: {name}")
        return None
    
    # Extract V2 Transaction Details
    v2_data = listing.get('v2', {})
    auction_house = v2_data.get('auctionHouseKey')
    seller_referral = v2_data.get('sellerReferral')
    expiry = v2_data.get('expiry')

    logger.info(f"✨ [Processed] {name} | Price: {price_sol} {price_currency}")

    return {
        'listing_id': listing_id, # Use the resolved, non-null ID
        'name': name,
        'grade_num': grade_num,
        'grade': grade,
        'category': category,
        'insured_value': insured_value,
        'grading_company': company,
        'img_url': listing.get('img'),
        'grading_id': cert_id,
        'token_mint': listing.get('mintAddress') or listing.get('tokenMint') or listing_id, # Fallback to listing_id if needed
        'price_amount': price_sol,
        'price_currency': price_currency, 
        'listed_at': listing.get('updatedAt'),
        'auction_house': auction_house,
        'seller_referral': seller_referral,
        'expiry': expiry,
    }

async def _fetch_with_retries_async(url: str, params: dict, retries: int = 5, initial_delay: float = 1.0):
    """Handles API calls asynchronously with error handling and retries."""
    delay = initial_delay
    for i in range(retries):
        try:
            # Use public_async_client for these idxv2 calls
            response = await public_async_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data.get('results', [])
            if isinstance(data, list):
                return data
            logger.warning(f"Unexpected data type from ME API: {type(data)}")
            return []
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"ME API connection/status error (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.critical("ME API fetch failed after multiple retries. The service may be down.")
    return []

    return []

async def _fetch_listings_async(processed_cache: dict | None, limit: int = 100, blacklisted_keywords: list[str] = None):
    """
    Unified async fetch function for the new API.
    processed_cache: Dict[mint_address, last_price]
    """
    base_url = "https://api-mainnet.magiceden.us/idxv2/getListedNftsByCollectionSymbol"
    
    params = {
        'collectionSymbol': 'collector_crypt',
        'limit': limit,
        'direction': 1,
        'field': 2,
        'attributes': json.dumps([
            {"attributes": [{"traitType": "Category", "value": "Pokemon"}]},
            {"attributes": [
                {"traitType": "Grading Company", "value": "PSA"},
                {"traitType": "Grading Company", "value": "Beckett"},
                {"traitType": "Grading Company", "value": "BGS"}
            ]}
        ]),
        'token22StandardFilter': 1,
        'mplCoreStandardFilter': 1,
        'mode': 'all',
        'agg': 3,
        'compressionMode': 'both'
    }
    
    new_listings = []
    
    logger.info(f"🔍 [Idxv2] Fetching recent listings (Limit: {limit})...")
    raw_listings = await _fetch_with_retries_async(base_url, params)
    
    # --- HEARTBEAT LOG (Requested by User) ---
    logger.info(f"❤️ [Heartbeat] Fetched {len(raw_listings) if raw_listings else 0} raw items from ME.")
    
    if not raw_listings:
        return new_listings, 0
    
    new_found_count = 0
    for listing in raw_listings:
        # CRITICAL FIX: Use Mint Address to match Activity Feed logic
        # Note: Idxv2 uses 'token_mint' (snake_case), not tokenMint
        listing_id = listing.get('token_mint') or listing.get('mintAddress') or listing.get('tokenMint') or listing.get('id')
        
        if processed_cache is not None:
             # Logic: If NEW mint OR (Known Mint AND Price Changed) -> Process
             last_price = processed_cache.get(listing_id)
             current_price = float(listing.get('price', 0))
             
             should_process = False
             if listing_id not in processed_cache:
                 should_process = True
             elif abs(last_price - current_price) > 0.01: # Float epsilon
                 logger.info(f"♻️ [Re-List] Price Change for {listing_id[:8]}: {last_price} -> {current_price}")
                 should_process = True
                 
             if should_process:
                # GLOBAL DEDUPLICATION: Attempt to acquire lock
                # This prevents Activity Monitor from processing the same item simultaneously
                acquired, reason = await PROCESSING_MANAGER.try_acquire(listing_id, float(listing.get('price', 0)))
                if not acquired:
                    continue

                try:
                    processed = _process_listing(listing, blacklisted_keywords)
                    if processed:
                        new_listings.append(processed)
                        new_found_count += 1
                    
                    # Update Cache immediately
                    processed_cache[listing_id] = current_price
                finally:
                    # Release lock and update internal ProcessingManager cache
                    await PROCESSING_MANAGER.release(listing_id, float(listing.get('price', 0)))
        else:
            # This branch is for initial population
            processed = _process_listing(listing, blacklisted_keywords)
            if processed:
                new_listings.append(processed)

    if new_found_count > 0:
        logger.info(f"Found {new_found_count} new listings from ME.")
                
    return new_listings, new_found_count

async def fetch_initial_listings_async(limit: int = 100, blacklisted_keywords: list[str] = None):
    """Fetches a specific number of recent listings for initial DB population, asynchronously."""
    logger.info(f"Fetching latest {limit} listings to populate database...")
    initial_listings, _ = await _fetch_listings_async(None, limit=limit, blacklisted_keywords=blacklisted_keywords)
    processed_ids = {listing['listing_id'] for listing in initial_listings if listing and listing.get('listing_id')} 
    # Compatibility: Convert set to dict with prices for initial load
    # (Actually fetch_initial_listings is usually for pop, we might just return the list/set logic as is, or update caller)
    # To be safe, we return the list. Caller will build the Cache.
    return initial_listings, processed_ids

async def fetch_latest_listings_async(processed_cache: dict, blacklisted_keywords: list[str] = None):
    """
    [Hybrid Mode] Fetches the 20 newest listings using the efficient IDXv2 endpoint.
    - Cost: 1 Request.
    - Benefit: Returns full details immediately.
    """
    return await _fetch_listings_async(processed_cache, limit=20, blacklisted_keywords=blacklisted_keywords)

async def fetch_new_listings_async(processed_cache: dict, processed_signatures: set = None, blacklisted_keywords: list[str] = None):
    """
    [Producer Logic] Fetches 'activity' events (list/delist/buy).
    - Rate Limit: Controls the 'burst' of detail checks.
    - Mechanism: Finds candidates -> Launches tasks -> Tasks wait on 'STATUS_CHECK_SEMAPHORE' (Max 2).
    Returns: (new_listings, sold_mints_set)
    """
    act_url = "https://api-mainnet.magiceden.dev/v2/collections/collector_crypt/activities"
    params = {'limit': 50}
    
    new_listings = []
    sold_mints = set()
    
    try:
        # 1. Fetch Activities
        t_start = time.time()
        response = await async_client.get(act_url, params=params)
        fetch_dur = time.time() - t_start
        
        # PERF LOG: Network Latency
        logger.info(f"📡 [PERF] ME Fetch Time: {fetch_dur:.3f}s")
        
        # Debug: Check Rate Limits
        rl_limit = response.headers.get('x-ratelimit-limit', 'N/A')
        rl_rem = response.headers.get('x-ratelimit-remaining', 'N/A')
        if response.status_code == 429:
             logger.critical(f"🛑 429 HIT! Headers: Limit={rl_limit}, Remaining={rl_rem}. SLEEPING LONG.")
             await asyncio.sleep(10) # Mandatory penalty box
        
        if response.status_code != 200:
             logger.warning(f"ME API Error {response.status_code}: RL-Limit={rl_limit}, RL-Rem={rl_rem}")
        
        response.raise_for_status()
        activities = response.json()
        
        candidates = []
        
        # 2. Filter for events
        for act in activities:
            # OPTIMIZATION: Signature Deduplication
            # Skip ANY event (list/sale) if we have processed its unique signature before.
            sig = act.get('signature')
            if processed_signatures is not None and sig:
                if sig in processed_signatures:
                    continue
                processed_signatures.add(sig)

            event_type = act.get('type')
            token = act.get('token', {})
            mint = token.get('mintAddress') or act.get('tokenMint')
            
            if not mint:
                continue
            
            # NOTE: We rely on processed_signatures for dedup here. 
            # We do NOT check processed_cache yet, because a new event might mean a price change.

            if event_type == 'list':
                candidates.append(mint)
            elif event_type in ['buyNow', 'delist', 'sale', 'buy']:
                sold_mints.add(mint)
        
        if not candidates:
            return new_listings, sold_mints
        


        # 3. Fetch Full Details for Candidates (Parallel)
        # We use gather to fetch multiple mints at once
        logger.debug(f"Found {len(candidates)} list events. Fetching details...")
         
        tasks = [check_listing_status_async(mint, retries=2) for mint in candidates]
        results = await asyncio.gather(*tasks)
        
        # 4. Process Results
        new_found_count = 0
        for raw_item in results:
            if raw_item and raw_item != 'not_found' and isinstance(raw_item, dict):
                # Canonical ID
                mint_key = raw_item.get('token_mint') or raw_item.get('mintAddress') or raw_item.get('tokenMint') or raw_item.get('id')
                current_price = float(raw_item.get('price', 0))
                
                # --- TRACE LOGGING (Watchlist) ---
                if mint_key in DEBUG_MINTS:
                    logger.warning(f"🔍 [WATCH] Processing Watchlist Mint: {mint_key} | Price: {current_price}")
                
                # --- GLOBAL DEDUPLICATION ---
                # Try to acquire lock for this specific deal version (Mint + Price)
                acquired, reason = await PROCESSING_MANAGER.try_acquire(mint_key, current_price)
                if not acquired:
                    if mint_key in DEBUG_MINTS:
                        logger.warning(f"🔍 [WATCH] Skipped {mint_key}: {reason}")
                    continue

                try:
                    processed = _process_listing(raw_item, blacklisted_keywords)
                    if processed:
                        # Validation
                        if processed.get('price_amount', 0) > 0:
                            new_listings.append(processed)
                            new_found_count += 1
                            # FIX: Update shared cache immediately to prevent Idxv2 from re-queuing
                            if processed_cache is not None:
                                processed_cache[mint_key] = current_price
                        else:
                            if mint_key in DEBUG_MINTS: logger.warning(f"🔍 [WATCH] Rejected {mint_key}: Price 0 or Invalid")
                    else:
                        if mint_key in DEBUG_MINTS: logger.warning(f"🔍 [WATCH] Rejected {mint_key}: _process_listing returned None")

                finally:
                    # Release lock and update cache if we processed it (even if rejected, we saw this price)
                    # Actually, if we rejected it, should we cache it? 
                    # Yes, otherwise we re-process rejection every cycle.
                    await PROCESSING_MANAGER.release(mint_key, current_price)
        if new_found_count > 0:
            logger.info(f"⚡ Found {new_found_count} fresh listings via Activity Feed!")

    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        
    return new_listings, sold_mints

async def get_wallet_activities_async(wallet_address: str, limit: int = 10):
    """
    Fetches recent activity for a specific wallet.
    Endpoint: /v2/wallets/{wallet_address}/activities
    """
    url = f"https://api-mainnet.magiceden.dev/v2/wallets/{wallet_address}/activities"
    params = {'offset': 0, 'limit': limit}
    
    try:
        # Use the authenticated client if available, else public
        # Assuming 'async_client' and 'public_async_client' are defined elsewhere
        # and 'api_key' is a variable indicating if an API key is present.
        # This part might need adjustment based on actual client setup.
        client = async_client # if api_key else public_async_client # Simplified for this context
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Wallet Activity Fetch Failed: {response.status_code} | {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching wallet activity for {wallet_address}: {e}")
        return []

async def fetch_all_listings_paginated_async(collection_symbol: str = 'collector_crypt', blacklisted_keywords: list[str] = None):
    """
    Fetches all listings for a given collection from Magic Eden's idxv2 API using pagination,
    with server-side filtering similar to other functions in this module.
    This is intended for a one-time full database sync.
    """
    logger.info(f"--- Starting full listing fetch for collection: {collection_symbol} using paginated idxv2 endpoint ---")
    all_listings = []
    
    # Base URL for the efficient idxv2 endpoint
    base_url = "https://api-mainnet.magiceden.us/idxv2/getListedNftsByCollectionSymbol"
    
    # Parameters with filters for Pokemon and graded cards, similar to fetch_new_listings_async
    # This ensures we only request and process relevant listings.
    params = {
        'collectionSymbol': collection_symbol,
        'limit': 100, # Fetch 100 items per page
        'direction': 1,
        'field': 2,
        'attributes': json.dumps([
            {"attributes": [{"traitType": "Category", "value": "Pokemon"}]},
            {"attributes": [
                {"traitType": "Grading Company", "value": "PSA"},
                {"traitType": "Grading Company", "value": "Beckett"},
                {"traitType": "Grading Company", "value": "BGS"}
            ]}
        ]),
        'token22StandardFilter': 1,
        'mplCoreStandardFilter': 1,
        'mode': 'all',
        'agg': 3,
        'compressionMode': 'both'
    }

    page_count = 0
    after_id = None # This will be our cursor for pagination

    while True:
        page_count += 1
        
        current_params = params.copy()
        if after_id:
            current_params['after'] = after_id

        logger.info(f"Fetching page {page_count} (limit {current_params['limit']})...")
        
        try:
            # Use the existing fetcher, which returns a list of raw listings
            raw_listings = await _fetch_with_retries_async(base_url, current_params)
            
            # If the API returns an empty list, we've reached the end.
            if not raw_listings:
                logger.info("No more listings found. Concluding fetch.")
                break

            logger.info(f"Received {len(raw_listings)} raw listings from page {page_count}.")

            for listing in raw_listings:
                processed = _process_listing(listing, blacklisted_keywords)
                if processed:
                    all_listings.append(processed)
            
            # Get the ID of the last item to use as the cursor for the next page.
            # If the ID is the same as the last one, we're in a loop.
            last_listing_id = raw_listings[-1].get('id')
            if not last_listing_id or last_listing_id == after_id:
                if not last_listing_id:
                    logger.warning("Could not find 'id' in the last listing to continue pagination. Stopping.")
                else:
                    logger.warning(f"Pagination cursor '{after_id}' did not change. Stopping to prevent infinite loop.")
                break
            
            after_id = last_listing_id

            # If we get less than the limit, it's the last page.
            if len(raw_listings) < current_params['limit']:
                logger.info(f"Received {len(raw_listings)} listings (less than limit). Assuming this is the last page.")
                break

            # Be respectful to the API by adding a delay between requests.
            logger.debug("Waiting for 2 seconds before next paginated request...")
            await asyncio.sleep(2) 

        except Exception as e:
            logger.exception(f"An error occurred during paginated fetch on page {page_count}.")
            break # Exit on error to avoid infinite loops

    logger.info(f"--- Fetched a total of {len(all_listings)} processed listings from Magic Eden. ---")
    return all_listings

async def check_listing_status_async(mint_address: str, retries: int = 5, initial_delay: float = 1.0) -> str | None:
    """
    Checks a single card's data asynchronously using the /v2/tokens/{mint} endpoint.
    Returns the full card data dictionary, or 'not_found'.
    """
    url = f"https://api-mainnet.magiceden.dev/v2/tokens/{mint_address}"
    delay = initial_delay
    for attempt in range(retries):
        try:
            async with STATUS_CHECK_SEMAPHORE:
                response = await async_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # DEBUG: Dump the raw data for the problematic mint to see what fields we can use
                if mint_address == "EBnLaJzkKcrtCA1N2ek2aBf8U8EB2orKuhXc4PCnYoN4":
                    logger.warning(f"🔍 [DEBUG RAW] Data for Sold Mint {mint_address}: {json.dumps(data)}")
                return data
            elif response.status_code == 404:
                return "not_found"
            else:
                response.raise_for_status() # Raise an exception for other bad statuses to trigger a retry
        except httpx.RequestError as e:
            logger.warning(f"ME API check for {mint_address} failed on attempt {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Request failed for {mint_address} status check after {retries} attempts.")
    return None
