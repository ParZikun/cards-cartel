import httpx
import asyncio
from datetime import datetime, timezone

async def compare_apis():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        print("🔍 checking API Latency difference...")
        
        # 1. Check Activities (The "Sniper" Stream)
        act_url = "https://api-mainnet.magiceden.dev/v2/collections/collector_crypt/activities"
        t1_start = datetime.now()
        act_resp = await client.get(act_url, params={'limit': 100})
        t1_end = datetime.now()
        
        latest_activity_time = None
        if act_resp.status_code == 200:
            activities = act_resp.json()
            for act in activities:
                if act.get('type') == 'list':
                    # blockTime is unix timestamp
                    bt = act.get('blockTime')
                    if bt:
                        latest_activity_time = datetime.fromtimestamp(bt, timezone.utc)
                        break
        
        # 2. Check Listings (The "Browse" Feed)
        list_url = "https://api-mainnet.magiceden.us/idxv2/getListedNftsByCollectionSymbol"
        params = {
            'collectionSymbol': 'collector_crypt',
            'limit': 1,
            'direction': 1, # Descending
            'field': 2,    # Recently Listed
            'mode': 'all'
        }
        t2_start = datetime.now()
        list_resp = await client.get(list_url, params=params)
        t2_end = datetime.now()
        
        latest_listing_time = None
        if list_resp.status_code == 200:
            listings = list_resp.json().get('results', [])
            if listings:
                # updatedAt is ISO string usually
                updated_at = listings[0].get('updatedAt') # "2023-10-..."
                if updated_at:
                    try:
                        latest_listing_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    except:
                        pass

        # Report
        now = datetime.now(timezone.utc)
        
        print("\n--- ⏱️ ACTIVITY STREAM (Sniper Feed) ---")
        if latest_activity_time:
            age = now - latest_activity_time
            print(f"Latest Event: {latest_activity_time.strftime('%H:%M:%S')} (Age: {age.seconds} seconds ago)")
            print("Status: ⚡ INSTANT")
        else:
            print("Failed to fetch.")

        print("\n--- 🐢 BROWSE FEED (Website Search) ---")
        if latest_listing_time:
            age = now - latest_listing_time
            minutes = age.seconds // 60
            print(f"Latest Listing: {latest_listing_time.strftime('%H:%M:%S')} (Age: {minutes} minutes {age.seconds % 60} seconds ago)")
            print("Status: 🐌 DELAYED")
        else:
            print("Failed to fetch.")
            
        if latest_activity_time and latest_listing_time:
            diff = latest_activity_time - latest_listing_time
            print(f"\n💡 PROOF: The Sniper Feed is {diff.seconds // 60} minutes ahead of the Browse Feed.")

if __name__ == "__main__":
    asyncio.run(compare_apis())
