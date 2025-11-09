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

if not AUTH_TOKEN or not COOKIE or not GRAPHQL_URL:
    raise ValueError("AUTH_TOKEN and COOKIE must be set in the .env file.")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'Referer': 'https://app.alt.xyz/',
    'Origin': 'https://app.alt.xyz',
    'authorization': f'Bearer {AUTH_TOKEN}',
    'Cookie': COOKIE
}

# Create a single, reusable async client
async_client = httpx.AsyncClient(headers=HEADERS, timeout=20)

CERT_ID_TO_ASSET_ID_CACHE = {}

async def get_asset_id_async(cert_id: str, retries: int = 5, initial_delay: float = 1.0):
    """
    Looks up an asset's internal ID using its certification number, asynchronously.
    """
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
                return None
            
            asset = data.get('data', {}).get('cert', {}).get('asset')
            if asset and 'id' in asset:
                return asset['id']
            else:
                logger.warning(f"Cert ID '{cert_id}' not found on ALT. This is not an error.")
                return None
                
        except httpx.RequestError as e:
            if isinstance(e, httpx.HTTPStatusError):
                logger.warning(
                    f"ALT API call (get_asset_id_async) failed for cert '{cert_id}' on attempt {attempt + 1} "
                    f"with status {e.response.status_code}: {e.response.text}"
                )
            else:
                logger.warning(
                    f"ALT API call (get_asset_id_async) failed for cert '{cert_id}' on attempt {attempt + 1}: {repr(e)}"
                )
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Failed to get asset_id for cert '{cert_id}' after {retries} attempts.")
    return None

async def get_alt_data_async(cert_id: str, grade: str, company: str, retries: int = 5, initial_delay: float = 1.0):
    """
    Main async orchestrator. Returns a dict with: alt_value, avg_price, supply, and confidence data.
    """
    asset_id = CERT_ID_TO_ASSET_ID_CACHE.get(cert_id)
    if not asset_id:
        asset_id = await get_asset_id_async(cert_id)
        if not asset_id: return None
        CERT_ID_TO_ASSET_ID_CACHE[cert_id] = asset_id
    
    details_query = """
    query AssetDetails($id: ID!, $tsFilter: TimeSeriesFilter!) {
      asset(id: $id) {
        altValueInfo(tsFilter: $tsFilter) {
          currentAltValue
          confidenceData {
            currentConfidenceMetric
            currentErrorLowerBound
            currentErrorUpperBound
            __typename
          }
          __typename
        }
        cardPops {
          ...CardPopBase
          __typename
        }
        __typename
      }
    }
    fragment CardPopBase on CardPop {
      gradingCompany
      gradeNumber
      count
      __typename
    }
    """
    transactions_query  = """
    query AssetMarketTransactions($id: ID!, $marketTransactionFilter: MarketTransactionFilter!) {
      asset(id: $id) {
        marketTransactions(marketTransactionFilter: $marketTransactionFilter) {
          ...MarketTransactionBase
          __typename
        }
        __typename
      }
    }
    fragment MarketTransactionBase on MarketTransaction {
      date
      price
      __typename
    }
    """
    details_payload =  {
        "operationName": "AssetDetails",
        "variables": {
            "id": asset_id,
            "tsFilter": {"gradeNumber": f"{float(grade):.1f}", "gradingCompany": company}
        },
        "query": details_query
    }
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
            # Run both GraphQL queries concurrently
            details_response, trans_response = await asyncio.gather(
                async_client.post(url=GRAPHQL_URL, json=details_payload),
                async_client.post(url=GRAPHQL_URL, json=trans_payload)
            )
            details_response.raise_for_status()
            trans_response.raise_for_status()

            details_json = details_response.json()
            trans_json = trans_response.json()

            if not details_json or not trans_json:
                logger.warning(f"Received empty JSON response for asset '{asset_id}'.")
                return None

            details_data = details_json.get('data', {}).get('asset', {}) or {}
            transactions = trans_json.get('data', {}).get('asset', {}).get('marketTransactions', [])

            alt_value_info = details_data.get('altValueInfo', {}) or {}
            confidence_data = alt_value_info.get('confidenceData', {}) or {}
            supply = 0
            card_pops = details_data.get('cardPops', [])
            for pop in card_pops:
                if pop.get('gradingCompany') == company and str(pop.get('gradeNumber')) == f"{float(grade):.1f}":
                    supply = pop.get('count', 0)
                    break

            avg_price = 0.0
            if supply > 3000:
                logger.debug("High supply detected. Using 15-day rolling average.")
                daily_prices, fifteen_days_ago = defaultdict(list), datetime.now() - timedelta(days=15)
                for tx in transactions:
                    tx_date = datetime.fromisoformat(tx['date'].split('T')[0])
                    if tx_date >= fifteen_days_ago:
                        daily_prices[tx_date.strftime('%Y-%m-%d')].append(float(tx['price']))
                if daily_prices:
                    daily_averages = [sum(prices) / len(prices) for prices in daily_prices.values()]
                    if daily_averages: avg_price = sum(daily_averages) / len(daily_averages)
            else:
                logger.debug("Low supply detected. Using last 4 recent sales.")
                num_to_avg = 4
                recent_sales = [float(tx['price']) for tx in transactions[:num_to_avg]]
                if recent_sales: avg_price = sum(recent_sales) / len(recent_sales)

            return {
                "alt_asset_id": asset_id,
                "alt_value": alt_value_info.get('currentAltValue') or 0.0,
                "avg_price": avg_price,
                "supply": supply,
                "lower_bound": confidence_data.get('currentErrorLowerBound') or 0.0,
                "upper_bound": confidence_data.get('currentErrorUpperBound') or 0.0,
                "confidence": confidence_data.get('currentConfidenceMetric') or 0.0
            }
        except httpx.RequestError as e:
            if isinstance(e, httpx.HTTPStatusError):
                logger.warning(
                    f"ALT API data fetch failed for asset {asset_id} on attempt {attempt + 1} with status {e.response.status_code}: {e.response.text}"
                )
            else:
                logger.warning(f"ALT API data fetch failed for asset {asset_id} on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Failed to get ALT data for asset {asset_id} after {retries} attempts.")
    return None # Explicitly return None if all retries fail

# --- SANITY TEST --- 
if __name__ == "__main__":
    async def run_test():
        example_cert_id = "114234980"
        example_grade = "9"
        example_company = "PSA"
        
        print("--- Running Standalone Async Test ---")
        processed_data = await get_alt_data_async(example_cert_id, example_grade, example_company)
        
        if processed_data:
            print("\n--- Processed Data ---")
            print(f"  - Asset id: {processed_data['alt_asset_id']}")
            print(f"  - Supply (Pop Count): {processed_data['supply']}")
            print(f"  - Alt Value: ${processed_data['alt_value']:.2f} (Confidence: {processed_data['confidence']}%)")
            print(f"  - Value Range: ${processed_data['lower_bound']:.2f} - ${processed_data['upper_bound']:.2f}")
            print(f"  - Calculated Avg. Price: ${processed_data['avg_price']:.2f}")
        else:
            print("\nCould not fetch and process ALT data for the given card.")

    asyncio.run(run_test())