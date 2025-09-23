import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

load_dotenv()
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

CERT_ID_TO_ASSET_ID_CACHE = {}

def get_asset_id(cert_id: str):
    """
    Looks up an asset's internal ID using its certification number.
    This is the crucial mapping function.
    """
    payload = {
        "operationName": "Cert",
        "variables": {"certNumber": cert_id},
        "query": "query Cert($certNumber: String!) { cert(certNumber: $certNumber) { asset { id name __typename } __typename } }"
    }
    
    try:
        response = requests.post(url=GRAPHQL_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()
        
        asset = data.get('data', {}).get('cert', {}).get('asset')
        if asset and 'id' in asset:
            return asset['id']
        else:
            print(f"WARN: Cert ID '{cert_id}' not found on ALT.")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"API call to get asset_id failed for cert '{cert_id}': {e}")
        return None

def get_alt_data(cert_id: str, grade: str, company: str):
    """
    Main orchestrator function. Returns a dict with: alt_value, avg_price, supply, and confidence data.
    """
    asset_id = CERT_ID_TO_ASSET_ID_CACHE.get(cert_id)
    if not asset_id:
        asset_id = get_asset_id(cert_id)
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
    
    try:
        details_response = requests.post(url=GRAPHQL_URL, headers=HEADERS, json=details_payload, timeout=5)
        details_response.raise_for_status()
        trans_response = requests.post(url=GRAPHQL_URL, headers=HEADERS, json=trans_payload, timeout=5)
        trans_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"An ALT API call failed for asset {asset_id}: {e}")
        return None

    details_data = details_response.json().get('data', {}).get('asset', {}) or {}
    transactions = trans_response.json().get('data', {}).get('asset', {}).get('marketTransactions', [])

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

# --- SANITY TEST ---
if __name__ == "__main__":
    example_cert_id = "114234980"
    example_grade = "9"
    example_company = "PSA"
    
    print("--- Running Standalone Test ---")
    processed_data = get_alt_data(example_cert_id, example_grade, example_company)
    
    if processed_data:
        print("\n--- Processed Data ---")
        print(f"  - Asset id: {processed_data['alt_asset_id']}")
        print(f"  - Supply (Pop Count): {processed_data['supply']}")
        print(f"  - Alt Value: ${processed_data['alt_value']:.2f} (Confidence: {processed_data['confidence']}%)")
        print(f"  - Value Range: ${processed_data['lower_bound']:.2f} - ${processed_data['upper_bound']:.2f}")
        print(f"  - Calculated Avg. Price: ${processed_data['avg_price']:.2f}")
    else:
        print("\nCould not fetch and process ALT data for the given card.")
