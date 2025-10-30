import sqlite3
import random
from datetime import datetime, timedelta

DB_FILE = "data/listings.db"

def create_dummy_deals():
    """
    Finds active, non-deal listings and randomly promotes them to deal categories
    for testing the /cartel_deals command.
    """
    print("--- Creating dummy deals for testing ---")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Find listings that are active but not already categorized as a deal
        cursor.execute("""
            SELECT listing_id FROM listings 
            WHERE is_listed = 1 AND cartel_category NOT IN ('AUTOBUY', 'GOOD', 'OK')
        """)
        listing_ids = [row[0] for row in cursor.fetchall()]
        random.shuffle(listing_ids)

        if len(listing_ids) < 15:
            print("⚠️ Not enough active listings in the database to create a full set of dummy deals.")
            print("   Run the initial population first (`make local-up` with an empty DB).")
            conn.close()
            return []

        # Assign categories
        deals_to_create = {
            "AUTOBUY": listing_ids[0:5],
            "GOOD": listing_ids[5:10],
            "OK": listing_ids[10:15]
        }

        total_updated = 0
        for category, ids in deals_to_create.items():
            cursor.executemany("UPDATE listings SET cartel_category = ? WHERE listing_id = ?", [(category, id) for id in ids])
            total_updated += cursor.rowcount
            print(f"✅ Assigned {len(ids)} listings to the '{category}' (deal) category.")
        
        conn.commit()
        conn.close()
        
        print(f"\nSuccessfully created {total_updated} dummy deals.")
        # Return the IDs of listings we just turned into deals, so we don't make them stale
        return listing_ids[0:15]

    except Exception as e:
        print(f"❌ An error occurred while creating dummy deals: {e}")
        return []

def make_data_stale(exclude_ids: list):
    """
    Updates the `last_analyzed_at` timestamp for 5 active listings to be much older,
    forcing the reaper/recheck to re-analyze them.
    """
    print("\n--- Forcing 5 active listings to become stale ---")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create a string of placeholders for the IN clause
        placeholders = ', '.join('?' for _ in exclude_ids)
        
        # Find 5 active listings that were NOT part of the dummy deals we just created
        query = f"""
            SELECT listing_id FROM listings 
            WHERE is_listed = 1 AND listing_id NOT IN ({placeholders}) 
            LIMIT 5
        """
        cursor.execute(query, exclude_ids)
        listing_ids_to_stale = [row[0] for row in cursor.fetchall()]

        if len(listing_ids_to_stale) < 5:
            print("⚠️ Could not find enough listings to mark as stale.")
            conn.close()
            return

        # Set the timestamp to over a year ago
        stale_timestamp = (datetime.utcnow() - timedelta(days=400)).isoformat()

        cursor.executemany("UPDATE listings SET last_analyzed_at = ? WHERE listing_id = ?", [(stale_timestamp, id) for id in listing_ids_to_stale])
        updated_rows = cursor.rowcount
        conn.commit()
        conn.close()

        if updated_rows > 0:
            print(f"✅ Successfully marked {updated_rows} listings as stale.")
            print("   You can now test `/recheck_all` or wait for the automated reaper to run.")
        else:
            print("⚠️ Could not find any active listings to mark as stale.")

    except Exception as e:
        print(f"❌ An error occurred while making data stale: {e}")

if __name__ == "__main__":
    # First, create the deals, and get the IDs of the listings we modified
    created_deal_ids = create_dummy_deals()
    
    # Then, make other listings stale, ensuring we don't touch the ones we just made deals
    if created_deal_ids:
        make_data_stale(exclude_ids=created_deal_ids)
