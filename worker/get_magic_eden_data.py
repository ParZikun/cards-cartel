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
async_client = httpx.AsyncClient(headers=HEADERS, timeout=10)

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

async def _fetch_with_retries_async(url: str, params: dict, retries: int = 3, delay: int = 5):
    """Handles API calls asynchronously with error handling and retries."""
    for i in range(retries):
        try:
            response = await async_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except httpx.RequestError as e:
            logger.warning(f"ME API connection error (attempt {i+1}/{retries}): {e}")
            await asyncio.sleep(delay)
    logger.critical("ME API fetch failed after multiple retries. The service may be down.")
    return None

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
        return new_listings
    
    for listing in raw_listings:
        listing_id = listing.get('id')
        
        if processed_ids is not None:
            if listing_id and listing_id not in processed_ids:
                processed = _process_listing(listing)
                if processed:
                    new_listings.append(processed)
                else:
                    processed_ids.add(listing_id)
            else:
                break
        else:
            processed = _process_listing(listing)
            if processed:
                new_listings.append(processed)
                
    return new_listings

async def fetch_initial_listings_async(limit: int = 100):
    """Fetches a specific number of recent listings for initial DB population, asynchronously."""
    logger.info(f"Fetching latest {limit} listings to populate database...")
    initial_listings = await _fetch_listings_async(None, limit=limit)
    processed_ids = {listing['listing_id'] for listing in initial_listings if listing and listing.get('listing_id')}
    return initial_listings, processed_ids

async def fetch_new_listings_async(processed_ids: set):
    """Fetches the most recent listings asynchronously and filters out any already processed."""
    return await _fetch_listings_async(processed_ids=processed_ids, limit=100)

async def check_listing_status_async(mint_address: str) -> str | None:
    """
    Checks a single card's data asynchronously using the /v2/tokens/{mint} endpoint.
    Returns the full card data dictionary, or 'not_found'.
    """
    url = f"https://api-mainnet.magiceden.dev/v2/tokens/{mint_address}"
    try:
        response = await async_client.get(url)
        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 404:
            return "not_found"
        else:
            logger.warning(f"ME API returned status {response.status_code} for {mint_address} during status check.")
            return None
    except httpx.RequestError as e:
        logger.error(f"Request failed for {mint_address} status check: {e}")
        return None
