import httpx
import json
import asyncio
import logging

# Initialize a logger for this module
logger = logging.getLogger(__name__)

# This list can be expanded as needed
BLACKLISTED_KEYWORDS = ['black star', 'sticker', 'stickers']

# Mimic a real browser request to ensure API access
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://magiceden.io',
    'Referer': 'https://magiceden.io/'
}

# Create a single, reusable async client
async_client = httpx.AsyncClient(headers=HEADERS, timeout=20)

def _get_attribute_value(attributes_list: list, target_trait: str):
    """Finds the value for a specific traitType within a list of attributes."""
    if not attributes_list: return None
    for attribute in attributes_list:
        if attribute.get('trait_type') == target_trait:
            return attribute.get('value')
    return None

def _process_listing(listing: dict):
    """
    Processes a single raw listing from the /idxv2/ API.
    Returns the processed dictionary or None if it's invalid.
    """
    if not listing: return None

    name = listing.get('content', "Unknown")
    for keyword in BLACKLISTED_KEYWORDS:
        if keyword in name.lower():
            logger.debug(f"Skipping blacklisted card: {name}")
            return None

    attributes = listing.get('attributes', [])
    company = _get_attribute_value(attributes, "Grading Company")
    if not company or company.upper() not in ["PSA", "BECKETT", "BGS"]: return None
    if company.upper() in ["BECKETT", "BGS"]: company = "BGS"

    category = "Card"
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
        logger.warning(f"Could not convert numeric value for '{name}'. Error: {e}. Skipping.")
        return None

    if not all([cert_id, name, grade, company]):
        logger.debug(f"Skipping card with missing critical data: {name}")
        return None
    
    if price_sol <= 0: return None

    return {
        'listing_id': listing.get('id'),
        'name': name,
        'grade_num': grade_num,
        'grade': grade,
        'category': category,
        'insured_value': insured_value,
        'grading_company': company,
        'img_url': listing.get('img'),
        'grading_id': cert_id,
        'token_mint': listing.get('mintAddress'),
        'price_amount': price_sol,
        'price_currency': 'SOL', 
        'listed_at': listing.get('updatedAt'), 
    }

async def _fetch_with_retries_async(url: str, params: dict, retries: int = 5, initial_delay: float = 1.0):
    """Handles API calls asynchronously with error handling and retries."""
    delay = initial_delay
    for i in range(retries):
        try:
            response = await async_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data.get('results', [])
            if isinstance(data, list):
                return data
            logger.warning(f"Unexpected data type from ME API: {type(data)}")
            return []
        except httpx.RequestError as e:
            logger.warning(f"ME API connection error (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.critical("ME API fetch failed after multiple retries. The service may be down.")
    return []

async def _fetch_listings_async(processed_ids: set | None, limit: int = 100):
    """Unified async fetch function for the new API."""
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
    raw_listings = await _fetch_with_retries_async(base_url, params)
    
    if not raw_listings:
        return new_listings, 0
    
    new_found_count = 0
    for listing in raw_listings:
        listing_id = listing.get('id')
        
        if processed_ids is not None:
            if listing_id and listing_id not in processed_ids:
                processed = _process_listing(listing)
                if processed:
                    new_listings.append(processed)
                    new_found_count += 1
                
                # Add to processed_ids here so we don't process it again
                processed_ids.add(listing_id)
        else:
            # This branch is for initial population, where we don't have processed_ids
            processed = _process_listing(listing)
            if processed:
                new_listings.append(processed)

    if new_found_count > 0:
        logger.info(f"Found {new_found_count} new listings from ME.")
                
    return new_listings, new_found_count

async def fetch_initial_listings_async(limit: int = 100):
    """Fetches a specific number of recent listings for initial DB population, asynchronously."""
    logger.info(f"Fetching latest {limit} listings to populate database...")
    initial_listings, _ = await _fetch_listings_async(None, limit=limit)
    processed_ids = {listing['listing_id'] for listing in initial_listings if listing and listing.get('listing_id')}
    return initial_listings, processed_ids

async def fetch_new_listings_async(processed_ids: set):
    """Fetches the most recent listings asynchronously and filters out any already processed."""
    new_listings, _ = await _fetch_listings_async(processed_ids=processed_ids, limit=100)
    return new_listings


async def fetch_all_listings_paginated_async(collection_symbol: str = 'collector_crypt'):
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
                processed = _process_listing(listing)
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
            response = await async_client.get(url)
            if response.status_code == 200:
                data = response.json()
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
