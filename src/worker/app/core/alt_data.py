import os
import httpx
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://alt-platform-server.production.internal.onlyalt.com/graphql/"
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
COOKIE = os.getenv("COOKIE")

if not AUTH_TOKEN or not COOKIE:
    # Changed to warning so we can run locally without full ENV if needed (though it will fail fetches)
    if os.getenv("ENVIRONMENT", "dev") != "local": 
        logger.warning("AUTH_TOKEN and COOKIE not set. Alt data fetching will fail.")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'Referer': 'https://app.alt.xyz/',
    'Origin': 'https://app.alt.xyz'
}
if AUTH_TOKEN:
    HEADERS['authorization'] = f'Bearer {AUTH_TOKEN}'
if COOKIE:
    HEADERS['Cookie'] = COOKIE

# Create a single, reusable async client
async_client = httpx.AsyncClient(headers=HEADERS, timeout=20)

CERT_ID_TO_ASSET_ID_CACHE = {}

async def get_asset_id_async(cert_id: str, retries: int = 5, initial_delay: float = 1.0):
    """
    Looks up an asset's internal ID using its certification number, asynchronously.
    """
    # Quick cache check
    if cert_id in CERT_ID_TO_ASSET_ID_CACHE:
        logger.debug(f"ℹ️ [Alt] Asset ID Cache Hit: {cert_id}")
        return CERT_ID_TO_ASSET_ID_CACHE[cert_id]

    payload = {
        "operationName": "Cert",
        "variables": {"certNumber": cert_id},
        "query": "query Cert($certNumber: String!) { cert(certNumber: $certNumber) { asset { id name __typename } __typename } }"
    }
    delay = initial_delay
    for attempt in range(retries):
        try:
            response = await async_client.post(url=GRAPHQL_URL, json=payload)
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(f"Received empty JSON response for cert '{cert_id}'. Assuming not found.")
                return None, None
            
            asset = data.get('data', {}).get('cert', {}).get('asset')
            if asset and 'id' in asset and 'name' in asset:
                CERT_ID_TO_ASSET_ID_CACHE[cert_id] = (asset['id'], asset['name'])
                return asset['id'], asset['name']
            else:
                logger.warning(f"Cert ID '{cert_id}' not found on ALT. This is not an error.")
                return None, None
                
        except httpx.RequestError as e:
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Failed to get asset_id for cert '{cert_id}' after {retries} attempts. Error: {e}")
    return None

async def get_alt_data_async(cert_id: str, grade: str, company: str, retries: int = 5, initial_delay: float = 1.0, fast_mode: bool = False):
    """
    Main async orchestrator. 
    Args:
        fast_mode: If True, skips fetching MarketTransactions (Price History) to speed up decision making.
    """
    logger.info(f"🔍 [Alt] Fetching data for Cert: {cert_id} (Fast: {fast_mode})")
    asset_id, asset_name = await get_asset_id_async(cert_id)
    if not asset_id: return None
    
    details_query = """
    query AssetDetails($id: ID!, $tsFilter: TimeSeriesFilter!) {
      asset(id: $id) {
        altValueInfo(tsFilter: $tsFilter) {
          currentAltValue
          confidenceData {
            currentConfidenceMetric
            currentErrorLowerBound
            currentErrorUpperBound
          }
        }
        cardPops {
          gradingCompany
          gradeNumber
          count
        }
      }
    }
    """
    transactions_query  = """
    query AssetMarketTransactions($id: ID!, $marketTransactionFilter: MarketTransactionFilter!) {
      asset(id: $id) {
        marketTransactions(marketTransactionFilter: $marketTransactionFilter) {
          date
          price
        }
      }
    }
    """
    
    # Payload for Valuation
    details_payload =  {
        "operationName": "AssetDetails",
        "variables": {
            "id": asset_id,
            "tsFilter": {"gradeNumber": f"{float(grade):.1f}", "gradingCompany": company}
        },
        "query": details_query
    }

    # Payload for History (Only needed if NOT fast_mode)
    trans_payload = {
        "operationName": "AssetMarketTransactions",
        "variables": {
            "id": asset_id,
            "marketTransactionFilter": {"gradingCompany": company, "gradeNumber": f"{float(grade):.1f}", "showSkipped": True}
        },
        "query": transactions_query
    }
    
    delay = initial_delay
    for attempt in range(retries):
        try:
            # Conditional Parallel Fetch
            if fast_mode:
                # FAST MODE: Check Value ONLY
                details_response = await async_client.post(url=GRAPHQL_URL, json=details_payload)
                trans_response = None
            else:
                # FULL MODE: Get everything
                details_response, trans_response = await asyncio.gather(
                    async_client.post(url=GRAPHQL_URL, json=details_payload),
                    async_client.post(url=GRAPHQL_URL, json=trans_payload)
                )
                trans_response.raise_for_status()

            details_response.raise_for_status()
            
            details_json = details_response.json()
            details_data = details_json.get('data', {}).get('asset', {}) or {}
            
            # --- Extract Core Value Data ---
            alt_value_info = details_data.get('altValueInfo', {}) or {}
            confidence_data = alt_value_info.get('confidenceData', {}) or {}
            
            # Supply
            supply = 0
            for pop in details_data.get('cardPops', []):
                if pop.get('gradingCompany') == company and str(pop.get('gradeNumber')) == f"{float(grade):.1f}":
                    supply = pop.get('count', 0)
                    break

            # Calculate Avg Price (Only if we have transactions)
            avg_price = 0.0
            if trans_response:
                trans_json = trans_response.json()
                transactions = trans_json.get('data', {}).get('asset', {}).get('marketTransactions', [])
                
                if supply > 3000:
                    daily_prices, fifteen_days_ago = defaultdict(list), datetime.now() - timedelta(days=15)
                    for tx in transactions:
                        tx_date = datetime.fromisoformat(tx['date'].split('T')[0])
                        if tx_date >= fifteen_days_ago:
                            daily_prices[tx_date.strftime('%Y-%m-%d')].append(float(tx['price']))
                    if daily_prices:
                        daily_averages = [sum(prices) / len(prices) for prices in daily_prices.values()]
                        if daily_averages: avg_price = sum(daily_averages) / len(daily_averages)
                else:
                    recent_sales = [float(tx['price']) for tx in transactions[:4]]
                    if recent_sales: avg_price = sum(recent_sales) / len(recent_sales)

            return {
                "alt_asset_id": asset_id,
                "alt_name": asset_name,
                "alt_value": alt_value_info.get('currentAltValue') or 0.0,
                "avg_price": avg_price,
                "supply": supply,
                "lower_bound": confidence_data.get('currentErrorLowerBound') or 0.0,
                "upper_bound": confidence_data.get('currentErrorUpperBound') or 0.0,
                "confidence": confidence_data.get('currentConfidenceMetric') or 0.0
            }

        except httpx.RequestError as e:
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Failed to get ALT data after {retries} attempts.")
    return None

if __name__ == "__main__":
    # Sanity Check
    async def run():
        print("Fetching Fast Mode...")
        res = await get_alt_data_async("114234980", "9", "PSA", fast_mode=True)
        print(f"Fast Mode Result: {res}")
    asyncio.run(run())