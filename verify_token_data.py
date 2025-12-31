import asyncio
import httpx
import json

async def verify_data():
    client = httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"})
    
    print("1. Fetching a recent 'list' activity to get a valid Mint Address...")
    act_url = "https://api-mainnet.magiceden.dev/v2/collections/collector_crypt/activities"
    
    try:
        resp = await client.get(act_url, params={'limit': 100})
        activities = resp.json()
        
        target_mint = None
        for act in activities:
            if act.get('type') == 'list':
                target_mint = act.get('token', {}).get('mintAddress')
                if target_mint:
                    print(f"Found Mint: {target_mint}")
                    break
        
        if not target_mint:
            print("No recent listing found to test. Try again later.")
            return

        print(f"\n2. Fetching Full Token Details for {target_mint}...")
        token_url = f"https://api-mainnet.magiceden.dev/v2/tokens/{target_mint}"
        
        token_resp = await client.get(token_url)
        token_data = token_resp.json()
        
        print("\n--- DATA CHECK ---")
        print(f"Name: {token_data.get('name')}")
        print(f"Mint: {token_data.get('mintAddress')}")
        print(f"Price: {token_data.get('price')} SOL")
        
        # Check critical autobuy fields
        # Note: These are usually inside a 'v2' object or top level depending on the endpoint specific version?
        # Let's inspect the Raw Keys to be sure.
        
        v2 = token_data.get('v2', {})
        print(f"\n[V2 Transaction Data]")
        print(f"Auction House: {v2.get('auctionHouseKey')}")
        print(f"Seller Referral: {v2.get('sellerReferral')}")
        print(f"Expiry: {v2.get('expiry')}")
        
        if v2.get('auctionHouseKey'):
            print("\n✅ SUCCESS: Auction House data is present!")
        else:
            print("\n⚠️ WARNING: Auction House data missing (This might be normal if it's not a V2 listing or different AH).")
            print("Raw Keys:", token_data.keys())
            if 'v2' in token_data:
                print("V2 Keys:", token_data['v2'].keys())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(verify_data())
