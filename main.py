import time
import database
import get_magic_eden_data as me
import get_alt_data as alt

def enrich_listings_with_alt_data(listings_to_process: list, slow_mode: bool = False):
    """
    Fetches ALT data for a list of listings and saves it to the database.
    Can run in a slow, respectful mode for enriching old listings.
    """
    total_listings = len(listings_to_process)
    for i, listing in enumerate(listings_to_process):
        start_time = time.time()
        
        prefix = f"Enriching old listing ({i+1}/{total_listings})" if slow_mode else "Processing new listing"
        print(f"  -> {prefix}: {listing.get('name')} ({listing.get('grading_id')})")
        
        try:
            processed_alt_data = alt.get_alt_data(
                cert_id=listing['grading_id'],
                grade=listing['grade_num'],
                company=listing['grading_company']
            )
            
            if processed_alt_data:
                # Save the enriched data back to the database
                database.update_listing_alt_data(listing['listing_id'], processed_alt_data)
                
                # For new listings, print the processing time metric
                if not slow_mode:
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"    ✅ Success. Processing took {duration:.3f} seconds.")
            else:
                print(f"    ⚠️ Could not fetch ALT data for {listing.get('name')}.")

        except Exception as e:
            print(f"    ❌ An unexpected error occurred while processing {listing.get('name')}: {e}")

        # If in slow mode for enriching old data, wait between requests
        if slow_mode:
            time.sleep(3) # Respectful delay to avoid flagging

def watchdog():
    """
    The main infinite loop that checks for and processes new listings at high speed.
    """
    print("\n--- 🚀 Starting Watchdog ---")
    
    # Load the IDs of all listings we have ever seen into memory
    processed_ids = database.get_all_listing_ids()
    print(f"Loaded {len(processed_ids)} previously processed listing IDs.")

    while True:
        try:
            print(f"\n[Watchdog at {time.strftime('%H:%M:%S')}] Checking for new listings...")
            new_listings = me.fetch_new_listings(processed_ids)
            
            if new_listings:
                print(f"🔥 Found {len(new_listings)} new items!")
                
                # 1. Save all new listings to the DB first to mark them as seen
                database.save_listings(new_listings)
                
                # 2. Update our in-memory set of processed IDs
                for item in new_listings:
                    processed_ids.add(item['listing_id'])
                
                # 3. Process each new listing to get ALT data immediately
                enrich_listings_with_alt_data(new_listings, slow_mode=False)
                
            else:
                print("✅ No new listings found.")

            # Wait before the next check
            time.sleep(0.6) # High-frequency check for new snipes

        except Exception as e:
            print(f"❌ An unexpected error occurred in the watchdog loop: {e}")
            print("Waiting for 10 seconds before retrying...")
            time.sleep(10)

if __name__ == "__main__":
    # 1. Ensure the database and table exist
    database.init_db()

    # 2. Check if the DB is empty. If so, do a one-time full population from ME.
    if not database.get_all_listing_ids():
        print("Database is empty. Performing one-time initial population from Magic Eden...")
        all_listings, _ = me.fetch_all_listings()
        if all_listings:
            database.save_listings(all_listings)
            print(f"✅ Initial ME population complete. Saved {len(all_listings)} listings.")
    
    # 3. Catch up on ALT data for any old listings that are missing it.
    # This runs once at startup.
    old_listings_to_enrich = database.get_listings_without_alt_data()
    if old_listings_to_enrich:
        print("\n--- Enriching Old Listings ---")
        enrich_listings_with_alt_data(old_listings_to_enrich, slow_mode=True)
        print("✅ Old listings enriched.")
    else:
        print("\n✅ All existing listings are already enriched.")
    
    # 4. Start the continuous watchdog for new listings
    watchdog()

