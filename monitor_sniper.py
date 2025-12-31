import asyncio
import httpx
import json
from datetime import datetime
import time

async def monitor_live_feed():
    url = "https://api-mainnet.magiceden.dev/v2/collections/collector_crypt/activities"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    
    print("👀 Starting Sniper Monitor (Press Ctrl+C to stop)...")
    print("Watching for NEW 'List' events on Magic Eden Activity Feed...")
    print("-" * 60)
    
    seen_signatures = set()
    initial_fetch_done = False
    
    async with httpx.AsyncClient(headers=headers) as client:
        while True:
            try:
                # 1. Poll Activities
                resp = await client.get(url, params={'limit': 100}) # Increased limit
                if resp.status_code == 200:
                    activities = resp.json()
                    
                    # Filter for list events
                    current_batch_list_events = [act for act in activities if act.get('type') == 'list']

                    if not initial_fetch_done:
                        # 1. Populate seen_signatures with EVERYTHING in the first batch to avoid "New" spam
                        for act in current_batch_list_events:
                            sid = act.get('signature')
                            if sid: seen_signatures.add(sid)

                        print(f"📜 RECENT HISTORY (Last 10 Listings):")
                        # Print top 10
                        for event in current_batch_list_events[:10]:
                            token = event.get('token', {})
                            mint = token.get('mintAddress') or event.get('tokenMint')
                            
                            # Fetch details for history items too
                            name = "Unknown"
                            currency = "SOL"
                            if mint:
                                try:
                                    t_url = f"https://api-mainnet.magiceden.dev/v2/tokens/{mint}"
                                    t_resp = await client.get(t_url)
                                    if t_resp.status_code == 200:
                                        t_data = t_resp.json()
                                        name = t_data.get('name', "Unknown")
                                        sol_price_data = t_data.get('solPrice', {})
                                        if sol_price_data.get('address') == 'EPjfwdd5SrqNsFC8CVU4FzJ8G8FpTE3j3v24g85r8rV':
                                            currency = "USDC"
                                except:
                                    pass
                            
                            if name == "Unknown" and mint:
                                name = f"Mint: {mint[:8]}..."
                                
                            price = event.get('price')
                            block_time = event.get('blockTime')
                            time_str = datetime.fromtimestamp(block_time).strftime('%H:%M:%S') if block_time else "?"
                            print(f"   [{time_str}] {name} | {price} {currency}")
                        
                        print("-" * 60)
                        print("👀 Live Monitoring Started... (Waiting for NEXT listing)")
                        initial_fetch_done = True
                        continue # Skip processing 'new_events' for this first batch
                    
                    # Logic for NEW events
                    new_events = []
                    for act in current_batch_list_events:
                        signature = act.get('signature')
                        if signature and signature not in seen_signatures:
                            new_events.append(act)
                            seen_signatures.add(signature)
                    
                    if new_events:
                        # Reverse to print Oldest -> Newest (Chronological flow)
                        new_events.reverse()
                        
                        print(f"   > Detected {len(new_events)} new events. Fetching details...")
                        
                        for event in new_events:
                            token = event.get('token', {})
                            mint = token.get('mintAddress') or event.get('tokenMint')
                            
                            raw_price = event.get('price')
                            
                            # 2. Fetch Full Details to resolve Name/Currency
                            token_url = f"https://api-mainnet.magiceden.dev/v2/tokens/{mint}"
                            currency = "SOL"
                            name = "Unknown"
                            category = "?"
                            
                            try:
                                t_resp = await client.get(token_url)
                                if t_resp.status_code == 200:
                                    t_data = t_resp.json()
                                    name = t_data.get('name', name)
                                    
                                    # Check Currency
                                    sol_price_data = t_data.get('solPrice', {})
                                    if sol_price_data.get('address') == 'EPjfwdd5SrqNsFC8CVU4FzJ8G8FpTE3j3v24g85r8rV':
                                        currency = "USDC"
                                        
                                    # Extract Category
                                    attrs = t_data.get('attributes', [])
                                    for a in attrs:
                                        if a.get('trait_type') == 'Category':
                                            category = a.get('value')
                                            break
                                    
                            except Exception as e:
                                name = f"Fetch Error ({mint})"
                            
                            block_time = event.get('blockTime')
                            time_str = "?"
                            if block_time:
                                dt = datetime.fromtimestamp(block_time)
                                time_str = dt.strftime('%H:%M:%S')
                            
                            print(f"[NEW LISTING @ {time_str}] {name}")
                            print(f"    Price: {raw_price} {currency} | Cat: {category} | Mint: {mint}")
                
                else:
                    print(f"API Error: {resp.status_code}")
                    
            except Exception as e:
                print(f"Error: {e}")
            
            # 2. Wait
            await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_live_feed())
    except KeyboardInterrupt:
        print("\nStopped.")
