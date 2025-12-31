import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from worker.app.core.magic_eden import fetch_latest_listings_async
from database.main import get_all_listing_ids, init_db

async def main():
    print("--- 🕵️‍♂️ DEBUG FEED DIAGNOSTIC ---")
    
    # 1. Load DB State
    print("1. Loading Local Database...")
    try:
        init_db()
        processed_ids = get_all_listing_ids()
        print(f"   ✅ Loaded {len(processed_ids)} known Mints from DB.")
    except Exception as e:
        print(f"   ❌ DB Error: {e}")
        return

    # 2. Fetch Live Data
    print("\n2. Fetching Live Magic Eden Data (Idxv2)...")
    try:
        # We pass empty set to force return of ALL items (no filtering inside the function if we can avoid it, 
        # but the function requires a set to filter. We'll pass an empty set to get everything returned, 
        # then check manually.)
        # Wait, the function modifies the set in place. 
        # Let's pass a copy or a new set to see what IT thinks is new.
        
        test_set = set() # Empty set means EVERYTHING is "New" to the function
        listings, count = await fetch_latest_listings_async(test_set)
        
        print(f"   ✅ API returned {len(listings)} listings.")
        
        print("\n3. Analyzing Results:")
        print(f"   {'STATUS':<15} | {'MINT':<44} | {'NAME'}")
        print("-" * 80)
        
        # DEBUG: Print structure of first item
        if listings:
             first = listings[0]
             print("\n🔍 RAW ITEM KEYS:", first.keys())
             print("🔍 SAMPLE ITEM:", first)
             print("-" * 20)
        
        for item in listings:
            # CRITICAL FIX: Include 'token_mint' (snake_case)
            mint = item.get('token_mint') or item.get('mintAddress') or item.get('tokenMint') or item.get('id') or "UNKNOWN_MINT"
            name = item.get('name') or "Unknown Name"
            
            # Additional safety for name containing non-ascii or being None
            name = str(name)
            mint = str(mint)
            
            status = "✅ KNOWN" if mint in processed_ids else "⚠️ NEW/MISSED"
            
            print(f"   {status:<15} | {mint:<44} | {name}")

    except Exception as e:
        print(f"   ❌ API Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
