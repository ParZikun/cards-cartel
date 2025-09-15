import requests
import time

# --- Cache Configuration ---
# We will store the price in memory. These variables will persist as long as the script is running.
_cached_sol_price = 0.0
_last_fetch_time = 0
CACHE_DURATION_SECONDS = 300  # 5 minutes (5 * 60)

def _fetch_sol_to_usdc_price():
    """
    Internal helper function to get the current price of 1 SOL in USDC from CoinGecko.
    This function is only called when the cache is stale.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['solana']['usd']
    except (requests.exceptions.RequestException, KeyError) as e:
        print(f"❌ ERROR: Could not fetch SOL price from CoinGecko: {e}")
        return None

def get_price_in_both_currencies(amount: float, currency: str):
    """
    Takes an amount in one currency (SOL or USDC) and returns a dictionary 
    with the value in both currencies, using a cached market rate.
    """
    global _cached_sol_price, _last_fetch_time

    # --- Caching Logic ---
    current_time = time.time()
    if (current_time - _last_fetch_time) > CACHE_DURATION_SECONDS:
        print("[Price] Cache is stale or empty. Fetching new SOL price from CoinGecko...")
        new_price = _fetch_sol_to_usdc_price()
        
        if new_price is not None:
            _cached_sol_price = new_price
            _last_fetch_time = current_time
            print(f"✅ New SOL price cached: ${_cached_sol_price:.2f}")
        else:
            print("⚠️ WARN: Failed to fetch new price. Using previous cached value (if available).")

    # --- Conversion Logic ---
    if _cached_sol_price == 0.0:
        print("❌ CRITICAL: Cannot perform price conversion, no cached price available.")
        return None # Cannot proceed without a price

    currency = currency.upper()
    if currency == 'SOL':
        sol_amount = amount
        usdc_amount = amount * _cached_sol_price
    elif currency == 'USDC':
        usdc_amount = amount
        sol_amount = amount / _cached_sol_price
    else:
        print(f"❌ ERROR: Invalid currency '{currency}'. Must be 'SOL' or 'USDC'.")
        return None
        
    return {
        'price_sol': sol_amount,
        'price_usdc': usdc_amount
    }

# --- Example Usage ---
if __name__ == "__main__":
    print("--- Testing Price Conversion Utility with Caching ---")
    
    # First call: Should fetch from the API
    print("\n[First Call]")
    prices1 = get_price_in_both_currencies(2.5, 'SOL')
    if prices1:
        print(f"  -> 2.5 SOL is worth ${prices1['price_usdc']:.2f}")

    # Second call: Should use the cache instantly
    print("\n[Second Call (should be instant)]")
    time.sleep(2) # Wait 2 seconds
    prices2 = get_price_in_both_currencies(150, 'USDC')
    if prices2:
        print(f"  -> $150 USDC is worth {prices2['price_sol']:.4f} SOL")

    print("\nCache will automatically refresh after 5 minutes on the next call.")

