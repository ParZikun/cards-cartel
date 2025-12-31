import asyncio
import httpx
import json
from datetime import datetime, timezone
import time

# --- CONFIG ---
COLLECTION = "collector_crypt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

async def fetch_token_details(client, mint):
    """Helper to fetch details and check if Pokemon"""
    if not mint: return None, None
    try:
        url = f"https://api-mainnet.magiceden.dev/v2/tokens/{mint}"
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            name = data.get('name', 'Unknown')
            return name, data.get('attributes', [])
    except:
        pass
    return "Unknown", []

def is_valid_pokemon(attributes):
    """Strict Filter Logic"""
    # 1. Category MUST be Pokemon
    cat = next((a['value'] for a in attributes if a['trait_type'] == 'Category'), None)
    if cat != 'Pokemon':
        return False
    
    # 2. Grading Company MUST be PSA/BGS (User's requirement)
    comp = next((a['value'] for a in attributes if a['trait_type'] == 'Grading Company'), None)
    valid_companies = ['PSA', 'BGS', 'BECKETT', 'Beckett']
    if not comp or comp not in valid_companies:
        return False
        
    return True

async def fetch_activities(client):
    """Source 1: Real-time Activity Stream (Manual Filter)"""
    url = f"https://api-mainnet.magiceden.dev/v2/collections/{COLLECTION}/activities"
    try:
        resp = await client.get(url, params={'limit': 100})
        if resp.status_code == 200:
            activities = resp.json()
            # Filter for Pokemon List Events
            for act in activities:
                if act.get('type') == 'list':
                    token = act.get('token', {})
                    mint = token.get('mintAddress') or act.get('tokenMint')
                    
                    # FETCH DETAILS
                    name, attrs = await fetch_token_details(client, mint)
                    
                    if is_valid_pokemon(attrs):
                        block_time = act.get('blockTime')
                        ts = datetime.fromtimestamp(block_time, timezone.utc) if block_time else datetime.now(timezone.utc)
                        return {
                            "source": "ACTVTY",
                            "name": name,
                            "price": act.get('price'),
                            "time": ts,
                            "mint": mint
                        }
            return None
    except Exception as e:
        return {"error": str(e)}
    return None

async def fetch_idxv2_listings(client):
    """Source 2: Frontend API (Native Filter)"""
    url = "https://api-mainnet.magiceden.us/idxv2/getListedNftsByCollectionSymbol"
    # Note: This API supports filters natively, so we trust it returns valid items.
    # But for rigorous comparison, we could double check? 
    # Let's trust it for now as it's the "Benchmark".
    params = {
        'collectionSymbol': COLLECTION,
        'limit': 20,
        'direction': 1, 
        'field': 2,    
        'attributes': json.dumps([
            {"attributes": [{"traitType": "Category", "value": "Pokemon"}]},
            {"attributes": [
                {"traitType": "Grading Company", "value": "PSA"},
                {"traitType": "Grading Company", "value": "Beckett"},
                {"traitType": "Grading Company", "value": "BGS"}
            ]}
        ])
    }
    try:
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            if results:
                item = results[0]
                t_str = item.get('updatedAt')
                ts = datetime.fromisoformat(t_str.replace('Z', '+00:00')) if t_str else datetime.now(timezone.utc)
                return {
                    "source": "IDXv2 ",
                    "name": item.get('content', item.get('title', 'Unknown')),
                    "price": item.get('price'),
                    "time": ts,
                    "mint": item.get('mintAddress')
                }
    except Exception as e:
        return {"error": str(e)}
    return None

async def fetch_v2_listings(client):
    """Source 3: Developer API Listings (Manual Filter)"""
    url = f"https://api-mainnet.magiceden.dev/v2/collections/{COLLECTION}/listings"
    params = {'limit': 20} # Fetch raw
    
    try:
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            results = resp.json()
            if results and isinstance(results, list):
                for item in results:
                    mint = item.get('tokenMint')
                    name, attrs = await fetch_token_details(client, mint)
                    
                    if is_valid_pokemon(attrs):
                        price = item.get('price')
                        return {
                            "source": "V2_API",
                            "name": name,
                            "price": price,
                            "time": None, 
                            "mint": mint
                        }
    except Exception as e:
        return {"error": str(e)}
    return None

async def race_loop():
    print("🏎️  STARTING RIGOROUS API RACE (Pokemon Only) 🏎️")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)
    print(f"{'SOURCE':<10} | {'LATEST POKEMON CARD':<35} | {'LISTED AT (UTC)':<12} | {'AGE'}")
    print("-" * 60)
    
    async with httpx.AsyncClient(headers=HEADERS) as client:
        while True:
            # Run all 3 in parallel
            tasks = [
                fetch_activities(client),
                fetch_idxv2_listings(client),
                fetch_v2_listings(client)
            ]
            
            results = await asyncio.gather(*tasks)
            
            act_res, idx_res, v2_res = results
            
            # Calculate Latest Time
            times = []
            if act_res and act_res.get('time'): times.append(act_res['time'])
            if idx_res and idx_res.get('time'): times.append(idx_res['time'])
            
            latest_time = max(times) if times else datetime.now(timezone.utc)
            
            # Print Rows
            row_printed = False
            for res in [act_res, idx_res, v2_res]:
                if not res: continue
                if "error" in res: continue
                
                name = res.get('name', 'Unknown')[:33]
                ts = res.get('time')
                
                age_str = "???"
                if ts:
                    time_str = ts.strftime('%H:%M:%S')
                    # Age relative to NOW
                    now = datetime.now(timezone.utc)
                    age = (now - ts).total_seconds()
                    age_str = f"{age:.1f}s"
                elif res['source'] == "V2_API":
                    time_str = "NO DATA"
                    age_str = "N/A"
                else:
                    time_str = "Unknown"
                    
                print(f"{res['source']:<10} | {name:<35} | {time_str:<12} | {age_str}")
                row_printed = True
            
            if not row_printed:
                print("... No Pokemon Found in Top 20/100 of any source ...")
            
            print("-" * 60)
            await asyncio.sleep(10) # Update every 10s

if __name__ == "__main__":
    try:
        asyncio.run(race_loop())
    except KeyboardInterrupt:
        print("\nRace Stopped.")
