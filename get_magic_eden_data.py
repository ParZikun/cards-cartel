import requests
import json
import re

def _get_attribute_value(listing_data: dict, target_trait: str):
    """
    Helper function to find the value for a specific traitType within a listing's attributes.
    """
    attributes_list = listing_data.get('token', {}).get('attributes', [])
    for attribute in attributes_list:
        if attribute.get('trait_type') == target_trait:
            return attribute.get('value')
    return None

def get_magic_eden_listings():
    """
    Fetches the most recent Pokémon card listings from Magic Eden.

    This function is designed for a "watchdog" to periodically check for new listings.
    It fetches only the first page of results (limit 50), which are the newest items.
    """
    collection_symbol = "collector_crypt"
    base_url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection_symbol}/listings"
    headers = {"accept": "application/json"}
    
    params = {
        'offset': 0,
        'limit': 50,
        'attributes': json.dumps([
            [{"traitType": "Category", "value": "Pokemon"}]
        ])
    }
    
    processed_listings = []
    
    # Regex to extract the card ID from the 'Location' field for PSA cards.
    psa_location_pattern = r"Collector Crypt[^\(]*\((\d+)\)"

    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        listings = response.json()

        if not listings:
            print("No recent listings found.")
            return processed_listings

        for listing in listings:
            name = _get_attribute_value(listing, "Name")
            
            # Skip bundles and boxes as per the logic
            if name and ("Bundle" in name or "Box" in name):
                continue
            
            grading_id = _get_attribute_value(listing, "Grading ID")
            grade = _get_attribute_value(listing, "The Grade")
            company = _get_attribute_value(listing, "Grading Company")
            
            # Logic to determine the correct card_id
            card_id = None
            if company == "PSA":
                location = _get_attribute_value(listing, "Location")
                if location:
                    match = re.search(psa_location_pattern, location)
                    if match:
                        card_id = match.group(1)
            
            # Fallback to grading_id if it's not a PSA card with a special location format
            if not card_id:
                card_id = grading_id
                
            if all([card_id, name, grade, company]):
                processed_listings.append({
                    'cert_id': card_id, # Standardized name for the final ID
                    'name': name,
                    'price': listing.get('price'),
                    'grade': grade,
                    'company': company,
                    'token_mint': listing.get('tokenMint'),
                    'img_url': listing.get('extra', {}).get('img')
                })
            else:
                # This helps debug if a listing is missing critical data
                print(f"⚠️ Skipping listing due to missing data. Name: {name}, Cert ID: {card_id}")

    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred while fetching Magic Eden data: {e}")
        return None # Return None on error

    return processed_listings

# --- Example Usage ---
# This block runs only when you execute this file directly.
if __name__ == "__main__":
    print("--- Fetching most recent Magic Eden listings (for sanity check) ---")
    
    # In your main pipeline, you will import and call get_magic_eden_listings()
    recent_listings = get_magic_eden_listings()
    
    if recent_listings is not None:
        print(f"\nSuccessfully fetched {len(recent_listings)} new listings.")
        
        if recent_listings:
            # Print the first 3 listings for a quick preview
            print("\n--- Sample of Recent Listings ---")
            for i, card in enumerate(recent_listings[:3]):
                print(f"\nListing {i+1}:")
                print(json.dumps(card, indent=2))
    else:
        print("\nFailed to fetch listings.")