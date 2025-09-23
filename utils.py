import requests
import time
import requests
import time
import logging

logger = logging.getLogger(__name__)

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
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data['solana']['usd']
    except (requests.exceptions.RequestException, KeyError) as e:
        logger.error(f"Could not fetch SOL price from CoinGecko: {e}")
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
        logger.info("Price cache is stale or empty. Fetching new SOL price...")
        new_price = _fetch_sol_to_usdc_price()
        if new_price is not None:
            _cached_sol_price = new_price
            _last_fetch_time = current_time
            logger.info(f"New SOL price cached: ${_cached_sol_price:.2f}")
        else:
            logger.warning(f"WARN: Failed to fetch new price. Using previous cached value (if available).")

    # --- Conversion Logic ---
    if _cached_sol_price == 0.0:
        logger.critical("Cannot perform price conversion, no cached price available.")
        return None # Cannot proceed without a price

    currency = currency.upper()
    if currency == 'SOL':
        return {'price_sol': amount, 'price_usdc': amount * _cached_sol_price}
    elif currency == 'USDC':
        return {'price_sol': amount / _cached_sol_price, 'price_usdc': amount}
    return None

def get_cc_data(token_mint: str):
    """
    Fetches the full card name and insured value from the Collector Crypt API.
    """
    if not token_mint: return None
    url = f"https://api.collectorcrypt.com/cards/publicNft/{token_mint}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://collectorcrypt.com/',
        'Origin': 'https://collectorcrypt.com'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        return {
            'name': data.get('itemName'),
            'created-at': data.get('createdAt')
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch Collector Crypt API data for mint {token_mint}: {e}")
        return None
    
# --- Example Usage ---
if __name__ == "__main__":
    data  = get_cc_data('HXaqbDSXmdwzPW9c2GR1uvEGJUSDPCF6BxJojLaU3rvb')
    print(data)
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

