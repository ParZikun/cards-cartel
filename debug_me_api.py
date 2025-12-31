import asyncio
import httpx
import json

async def check_api():
    base_url = "https://api-mainnet.magiceden.us/idxv2/getListedNftsByCollectionSymbol"
    
    # Remove attribute filters to test if they are excluding new items
    # attributes = json.dumps([...]) 


    print(f"Testing Sort Parameters for {base_url}...")
    
    async with httpx.AsyncClient() as client:
        # Test Fields 1-6
        for field in [1, 2, 3, 4, 5, 6]:
            params = {
                'collectionSymbol': 'collector_crypt',
                'limit': 1,
                'direction': 2, # Usually 1 is Ascending, 2 is Descending
                'field': field,
                # 'attributes': attributes, # REMOVED
                'mode': 'all',
                'agg': 3
            }
            
            try:
                resp = await client.get(base_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get('results', [])
                    if results:
                        item = results[0]
                        updated = item.get('updatedAt')
                        print(f"Field {field} | Dir 1: {updated}")
                    else:
                        print(f"Field {field} | Dir 1: No Results")
                        
                # Test Direction 2 (Ascending?)
                params['direction'] = 2
                resp = await client.get(base_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get('results', [])
                    if results:
                        item = results[0]
                        updated = item.get('updatedAt')
                        print(f"Field {field} | Dir 2: {updated}")

            except Exception as e:
                print(f"Field {field}: Error {e}")
                
        # --- Test Activities API ---
        print("\nTesting Activities API (v2/collections/collector_crypt/activities)...")
        act_url = "https://api-mainnet.magiceden.dev/v2/collections/collector_crypt/activities"
        # params = {'limit': 10, 'type': 'list'}
        # Activities often have a different structure
        try:
            resp = await client.get(act_url, params={'limit': 20}) # Increased limit
            if resp.status_code == 200:
                acts = resp.json()
                found_count = 0
                for i, act in enumerate(acts):
                     if act.get('type') == 'list':
                         date = act.get('blockTime') # Timestamp?
                         # Convert timestamp if int
                         import datetime
                         if isinstance(date, int):
                             date = datetime.datetime.fromtimestamp(date, datetime.timezone.utc)
                         
                         name = act.get('token', {}).get('name')
                         price = act.get('price')
                         # Add collection or attributes check if needed, but 'collector_crypt' is the collection
                         print(f"[Activity {i}] {date} | {name} | {price} SOL")
                         found_count += 1
                if found_count == 0:
                    print("No 'list' activities found in recent batch.")
            else:
                print(f"Activities Error: {resp.status_code}")
        except Exception as e:
            print(f"Activities Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_api())
