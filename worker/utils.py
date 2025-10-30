import requests
import time
import requests
import time
import logging
from datetime import datetime, timedelta

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

def convert_utc_to_cdt(utc_time_str):
    # Convert UTC time string to a datetime object
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Subtract 5 hours to convert to CDT
    cdt_time = utc_time - timedelta(hours=5)
    
    # Return the time in the format "dd/mm/yyyy at hh:mm:ss"
    return cdt_time.strftime("%d/%m/%Y at %H:%M:%S")
