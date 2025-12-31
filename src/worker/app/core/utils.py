import httpx
import time
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- Thread-safe Caching Mechanism ---
_cached_sol_price = 0.0
_last_fetch_time = 0
_cache_lock = asyncio.Lock()
CACHE_DURATION_SECONDS = 300  # 5 minutes

# Use a single, reusable async client for performance
async_client = httpx.AsyncClient(timeout=10)

async def _fetch_sol_to_usdc_price():
    """
    Internal async helper to get the current SOL price in USDC from CoinGecko.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
    try:
        response = await async_client.get(url)
        response.raise_for_status()
        data = response.json()
        return data['solana']['usd']
    except (httpx.RequestError, KeyError) as e:
        logger.error(f"Could not fetch SOL price from CoinGecko: {e}")
        return None

async def get_price_in_both_currencies(amount: float, currency: str) -> dict | None:
    """
    Takes an amount in one currency (SOL or USDC) and returns a dictionary 
    with the value in both currencies, using a thread-safe, async, cached market rate.
    """
    global _cached_sol_price, _last_fetch_time

    # --- Async and Thread-Safe Caching Logic ---
    async with _cache_lock:
        current_time = time.time()
        if (current_time - _last_fetch_time) > CACHE_DURATION_SECONDS:
            logger.info("Price cache is stale or empty. Fetching new SOL price...")
            new_price = await _fetch_sol_to_usdc_price()
            if new_price is not None:
                _cached_sol_price = new_price
                _last_fetch_time = current_time
                logger.info(f"New SOL price cached: ${_cached_sol_price:.2f}")
            else:
                logger.warning("Failed to fetch new price. Using previous cached value (if available).")

    # --- Conversion Logic ---
    if _cached_sol_price == 0.0:
        logger.critical("Cannot perform price conversion, no cached price available.")
        return None  # Cannot proceed without a price

    currency = currency.upper()
    if currency == 'SOL':
        return {'price_sol': amount, 'price_usdc': amount * _cached_sol_price}
    elif currency == 'USDC':
        # Avoid division by zero if price is somehow still zero
        if _cached_sol_price > 0:
            return {'price_sol': amount / _cached_sol_price, 'price_usdc': amount}
    return None


def normalize_name(name: str) -> str:
    """
    Normalizes a card name for comparison by removing specific punctuation and spaces.
    """
    if not name: return ""
    import re
    # Remove all non-alphanumeric characters (keep only letters and numbers)
    return re.sub(r'[^a-zA-Z0-9]', '', name.lower())


def calculate_token_overlap(name1: str, name2: str) -> float:
    """
    Calculates the percentage of important tokens from the shorter name 
    that are present in the longer name. Returns a float between 0.0 and 1.0.
    """
    if not name1 or not name2:
        return 0.0
    
    import re
    
    # helper to tokenize
    def tokenize(text):
        # lower, remove non-alphanumeric (keep spaces as separator)
        clean = re.sub(r'[^a-z0-9\s]', '', text.lower())
        tokens = set(clean.split())
        return tokens

    set1 = tokenize(name1)
    set2 = tokenize(name2)
    
    # Remove insignificant common words
    # "1st" and "shadowless" ARE important.
    # But "pokemon", "psa", "bgs" are noise.
    refined_ignore = {'pokemon', 'psa', 'bgs', 'cgc', 'card', 'tcg', 'en', 'jp', 'english', 'japanese'}
    
    set1 = {t for t in set1 if t not in refined_ignore}
    set2 = {t for t in set2 if t not in refined_ignore}
    
    if not set1 or not set2:
        return 0.0

    # Calculate intersection
    intersection = set1.intersection(set2)
    
    # We want to know if the defining characteristics of one are in the other.
    # Use the smaller set as the denominator to handle "Charizard vs Charizard PSA 10"
    min_len = min(len(set1), len(set2))
    
    if min_len == 0: return 0.0
    
    return len(intersection) / min_len

