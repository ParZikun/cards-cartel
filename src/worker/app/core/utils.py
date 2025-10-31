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

