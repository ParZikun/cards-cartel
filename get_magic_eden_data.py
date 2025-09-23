import requests
import json
import time
import re
from datetime import datetime, timezone
import logging
import utils

logger = logging.getLogger(__name__)

BLACKLISTED_KEYWORDS = ['black star', 'sticker', 'stickers']

def _get_attribute_value(attributes_list: list, target_trait: str):
    """Finds the value for a specific traitType within a list of attributes."""
    for attribute in attributes_list:
        if attribute.get('trait_type') == target_trait:
            return attribute.get('value')
    return None

def _process_listing(listing: dict):
    """
    Processes a single raw listing from the API into our desired dictionary format.
    Returns the processed dictionary or None if it's invalid.
    """
    token_data = listing.get('token', {})
    if not token_data: return None

    attributes = token_data.get('attributes', [])

    # --- Primary Filtering ---
    company = _get_attribute_value(attributes, "Grading Company")
    if not company or company.upper() not in ["PSA", "BECKETT", "BGS"]: return None
    if company.upper() in ["BECKETT", "BGS"]: company = "BGS"
    
    token_mint = listing.get('tokenMint')
    name = ''
    created_at = None
    if token_mint:
        cc_data = utils.get_cc_data(token_mint)
        if cc_data and cc_data.get('name'):
            name = cc_data['name']
            created_at = cc_data.get('created-at')
        else:
            # Fallback to ME data if the CC API fails for any reason
            name = token_data.get('name', "Unknown")
            created_at = None

    for keyword in BLACKLISTED_KEYWORDS:
        if keyword in name.lower():
            logger.debug(f"Skipping blacklisted card: {name}")
            return None
            
    # --- Categorization ---
    category = "Card"
    if name and "Bundle" in name:
        category = "Bundle"
    elif name and "Box" in name:
        category = "Box"

    # --- Data Extraction ---
    grade = _get_attribute_value(attributes, "The Grade")
    cert_id = _get_attribute_value(attributes, "Grading ID")
    insured_value_str = _get_attribute_value(attributes, "Insured Value")
    
    # Ensure all critical data points are present
    if not all([cert_id, name, grade, company]):
        return None
    
    grade_num = 0.0
    match = re.search(r'\d+(\.\d+)?', str(grade))
    if match:
        try:
            grade_num = float(match.group(0))
        except (ValueError, TypeError):
            pass 

    # Safely convert insured value to float
    insured_value = 0.0
    if insured_value_str:
        try:
            insured_value = float(insured_value_str.replace(',', ''))
        except (ValueError, TypeError):
            pass

    return {
        'listing_id': listing.get('pdaAddress'),
        'name': name,
        'grade_num': grade_num,
        'grade': grade,
        'category': category,
        'insured_value': insured_value,
        'grading_company': company,
        'img_url': listing.get('extra', {}).get('img'),
        'grading_id': cert_id,
        'token_mint': token_mint,
        'price_amount': listing.get('price'),
        'price_currency': 'SOL', 
        'created_at': created_at
    }

def _fetch_with_retries(url: str, params: dict, headers: dict, retries: int = 3, delay: int = 5):
    """Handles ME API calls with error handling and retries."""
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ME API connection error ({i+1}/{retries}): {e}")
            time.sleep(delay)
    logger.critical("ME API fetch failed after multiple retries.")
    return None

def fetch_initial_listings(limit: int = 100):
    """
    Fetches a specific number of the most recent listings for initial DB population.
    """
    logger.info(f"Fetching latest {limit} listings to populate database...")
    collection_symbol = "collector_crypt"
    base_url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection_symbol}/listings"
    headers = {"accept": "application/json"}
    params = {
        'offset': 0, 'limit': limit, 'sort': 'updatedAt', 'sort_direction': 'desc',
        'attributes': json.dumps([[{"traitType": "Category", "value": "Pokemon"}]])
    }
    initial_listings = []
    processed_ids = set()

    listings = _fetch_with_retries(base_url, params, headers)
    if listings:
        logger.debug(f"Raw ME API response for initial fetch: {len(listings)}")
        for listing in listings:
            processed = _process_listing(listing)
            if processed:
                initial_listings.append(processed)
                processed_ids.add(processed['listing_id'])
    return initial_listings, processed_ids

def fetch_new_listings(processed_ids: set):
    """
    Fetches the most recent listings sorted by update time and intelligently
    filters out any that have already been processed.
    """
    collection_symbol = "collector_crypt"
    base_url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection_symbol}/listings"
    headers = {"accept": "application/json"}
    
    params = {
        'offset': 0,
        'limit': 100, # Fetch the max allowed to ensure we see all new items
        'sort': 'updatedAt',
        'sort_direction': 'desc',
        'attributes': json.dumps([[{"traitType": "Category", "value": "Pokemon"}]])
    }
    new_listings = []
    listings = _fetch_with_retries(base_url, params, headers)
    
    if listings:
        for listing in listings:
            listing_id = listing.get('pdaAddress')
            if listing_id and listing_id not in processed_ids:
                processed = _process_listing(listing)
                if processed:
                    new_listings.append(processed)
            else:
                break
    
    return list(reversed(new_listings))
    # new_listings = []
    
    # try:
    #     response = requests.get(base_url, headers=headers, params=params)
    #     response.raise_for_status()
    #     listings = response.json()
        
    #     for listing in listings:
    #         listing_id = listing.get('pdaAddress')
    #         if listing_id and listing_id not in processed_ids:
    #             # This is a new listing. Process it.
    #             processed = _process_listing(listing, is_new=True)
    #             if processed:
    #                 new_listings.append(processed)
    #         else:
    #             # **CRITICAL OPTIMIZATION**
    #             # Because the API response is sorted by newest, the moment we
    #             # find a listing we've already seen, we can stop checking.
    #             break
    
    # except requests.exceptions.RequestException as e:
    #     print(f"❌ An error occurred during new listings fetch: {e}")
    #     return []

    # return list(reversed(new_listings))

# --- Sanity Check / Example Usage ---
if __name__ == "__main__":
    
    # 1. On the very first run, populate everything
    # all_listings, processed_ids_set = fetch_all_listings()
    all_listings, processed_ids_set = fetch_initial_listings()
    print(f"\n✅ Initial population complete. Found {len(all_listings)} listings.")
    print(f"Total unique listing IDs stored: {len(processed_ids_set)}")

    # 2. Simulate the watchdog loop
    print("\n--- Simulating Watchdog (running 3 checks) ---")
    for i in range(3):
        print(f"\n[Watchdog Check #{i+1}]")
        new_items = fetch_new_listings(processed_ids_set)
        
        if new_items:
            print(f"🔥 Found {len(new_items)} new items!")
            for item in new_items:
                print(f"  -> Processing: {item['name']} ({item['listing_id']})")
                processed_ids_set.add(item['listing_id'])
            print(f"Total processed IDs is now: {len(processed_ids_set)}")
        else:
            print("✅ No new listings found.")
        
        if i < 2: # Don't sleep on the last iteration
             time.sleep(2)