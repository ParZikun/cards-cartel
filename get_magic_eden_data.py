import requests
import json
import time
from datetime import datetime, timezone

# TESTED WORKING WELL
def _get_attribute_value(attributes_list: list, target_trait: str):
    """Finds the value for a specific traitType within a list of attributes."""
    for attribute in attributes_list:
        if attribute.get('trait_type') == target_trait:
            return attribute.get('value')
    return None

def _process_listing(listing: dict, is_new: bool):
    """
    Processes a single raw listing from the API into our desired dictionary format.
    Returns the processed dictionary or None if it's invalid.
    """
    token_data = listing.get('token', {})
    if not token_data:
        return None
        
    attributes = token_data.get('attributes', [])
    
    # --- Primary Filtering ---
    # User changed "BGS" to "Beckett"
    company = _get_attribute_value(attributes, "Grading Company")
    if company not in ["PSA", "Beckett"]:
        return None 

    name = token_data.get('name')
    
    category = "Card"
    if name and "Bundle" in name:
        category = "Bundle"
    elif name and "Box" in name:
        category = "Box"

    # --- Data Extraction ---
    grade_num = _get_attribute_value(attributes, "GradeNum")
    grade = _get_attribute_value(attributes, "Grade")
    cert_id = _get_attribute_value(attributes, "Grading ID")
    insured_value_str = _get_attribute_value(attributes, "Insured Value")
    
    # Ensure all critical data points are present
    if not all([cert_id, name, grade, company]):
        return None
    
    # Safely convert insured value to float
    insured_value = 0.0
    if insured_value_str:
        try:
            insured_value = float(insured_value_str.replace(',', ''))
        except (ValueError, TypeError):
            pass # Keep it 0.0 if parsing fails

    # Set timestamp only if it's a new listing
    timestamp = datetime.now(timezone.utc).isoformat() if is_new else None

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
        'token_mint': listing.get('tokenMint'),
        'price_sol': listing.get('price'), 
        'listed_at': timestamp
    }

def fetch_all_listings():
    """
    Fetches ALL Pokémon listings from Magic Eden by handling pagination.
    Returns a tuple: (list_of_all_listings, set_of_all_listing_ids).
    """
    print("🚀 Starting full data fetch. This may take a while...")
    collection_symbol = "collector_crypt"
    base_url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection_symbol}/listings"
    headers = {"accept": "application/json"}
    
    all_processed_listings = []
    processed_listing_ids = set()
    offset = 0
    limit = 100

    while True:
        params = {
            'offset': offset,
            'limit': limit,
            'attributes': json.dumps([[{"traitType": "Category", "value": "Pokemon"}]])
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            listings = response.json()

            if not listings:
                print("✅ No more listings found. Full fetch complete.")
                break

            print(f"Fetched {len(listings)} listings from offset {offset}...")
            
            for listing in listings:
                # Process with is_new=False since this is the initial population
                processed = _process_listing(listing, is_new=False)
                if processed:
                    all_processed_listings.append(processed)
                    processed_listing_ids.add(processed['listing_id'])
            
            offset += limit
            time.sleep(0.6)

        except requests.exceptions.RequestException as e:
            print(f"❌ An error occurred during full fetch: {e}")
            break
            
    return all_processed_listings, processed_listing_ids

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
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        listings = response.json()
        
        for listing in listings:
            listing_id = listing.get('pdaAddress')
            if listing_id and listing_id not in processed_ids:
                # This is a new listing. Process it.
                processed = _process_listing(listing, is_new=True)
                if processed:
                    new_listings.append(processed)
            else:
                # **CRITICAL OPTIMIZATION**
                # Because the API response is sorted by newest, the moment we
                # find a listing we've already seen, we can stop checking.
                break
    
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during new listings fetch: {e}")
        return []

    # The list is newest-to-oldest, reverse it to process in chronological order
    return list(reversed(new_listings))

# --- Sanity Check / Example Usage ---
if __name__ == "__main__":
    
    # 1. On the very first run, populate everything
    all_listings, processed_ids_set = fetch_all_listings()
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