import os
import requests
import json
from dotenv import load_dotenv

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
        print(f"ERROR: API call to get asset_id failed for cert '{cert_id}': {e}")
        return None

def get_asset_details(asset_id: str, grade: str, company: str):
    """
    NEW: Fetches asset details, including Alt Value, confidence, and card populations.
    """
    query = """
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
    payload = {
        "operationName": "AssetDetails",
        "variables": {
            "id": asset_id,
            "tsFilter": {"gradeNumber": f"{float(grade):.1f}", "gradingCompany": company}
        },
        "query": query
    }
    try:
        response = requests.post(url=GRAPHQL_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: API call to get asset details failed for asset '{asset_id}': {e}")
        return None

def get_asset_market_transactions(asset_id: str, grade: str, company: str):
    """
    Fetches ONLY the recent market transactions for a specific asset using the simplified endpoint.
    """
    query = """
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
    payload = {
        "operationName": "AssetMarketTransactions",
        "variables": {
            "id": asset_id,
            "marketTransactionFilter": {"gradingCompany": company, "gradeNumber": f"{float(grade):.1f}", "showSkipped": True}
        },
        "query": query
    }
    try:
        response = requests.post(url=GRAPHQL_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('asset', {}).get('marketTransactions', [])
    except requests.exceptions.RequestException as e:
        print(f"ERROR: API call to get transactions failed for asset '{asset_id}': {e}")
        return []

def get_alt_data(cert_id: str, grade: str, company: str):
    """
    Main orchestrator function. Returns a dict with: alt_value, avg_price, supply, and confidence data.
    """
    asset_id = CERT_ID_TO_ASSET_ID_CACHE.get(cert_id)
    if not asset_id:
        asset_id = get_asset_id(cert_id)
        if not asset_id: return None
        CERT_ID_TO_ASSET_ID_CACHE[cert_id] = asset_id

    # --- Step 1: Get Details (Alt Value & Supply) ---
    details_data = get_asset_details(asset_id, grade, company)
    if not details_data or not details_data.get('data', {}).get('asset'):
        return None
        
    asset_data = details_data['data']['asset']
    alt_value_info = asset_data.get('altValueInfo', {})
    confidence_data = alt_value_info.get('confidenceData', {})
    
    # Extract core values
    alt_value = alt_value_info.get('currentAltValue', 0.0)
    lower_bound = confidence_data.get('currentErrorLowerBound', 0.0)
    upper_bound = confidence_data.get('currentErrorUpperBound', 0.0)
    confidence = confidence_data.get('currentConfidenceMetric', 0.0)
    
    # Extract supply
    supply = 0
    card_pops = asset_data.get('cardPops', [])
    for pop in card_pops:
        if pop.get('gradingCompany') == company and str(pop.get('gradeNumber')) == f"{float(grade):.1f}":
            supply = pop.get('count', 0)
            break

    # --- Step 2: Get Transactions for Avg Price ---
    transactions = get_asset_market_transactions(asset_id, grade, company)

    # --- Step 3: Calculate Avg Price based on Supply ---
    num_to_avg = 4 if 0 < supply < 3000 else 10
    recent_sales = [float(tx['price']) for tx in transactions[:num_to_avg]]
    avg_price = sum(recent_sales) / len(recent_sales) if recent_sales else 0

    return {
        "asset_id": asset_id or None,
        "alt_value": alt_value or 0.0,
        "avg_price": avg_price or 0.0,
        "supply": supply or 0,
        "lower_bound": lower_bound or 0.0,
        "upper_bound": upper_bound or 0.0,
        "confidence": confidence or 0.0
    }

# --- SANITY TEST ---
if __name__ == "__main__":
    example_cert_id = "125552008"
    example_grade = "10"
    example_company = "PSA"
    
    print("--- Running Standalone Test ---")
    processed_data = get_alt_data(example_cert_id, example_grade, example_company)
    
    if processed_data:
        print("\n--- Processed Data ---")
        print(f"  - Asset id: {processed_data['asset_id']}")
        print(f"  - Supply (Pop Count): {processed_data['supply']}")
        print(f"  - Alt Value: ${processed_data['alt_value']:.2f} (Confidence: {processed_data['confidence']}%)")
        print(f"  - Value Range: ${processed_data['lower_bound']:.2f} - ${processed_data['upper_bound']:.2f}")
        print(f"  - Calculated Avg. Price: ${processed_data['avg_price']:.2f}")
    else:
        print("\nCould not fetch and process ALT data for the given card.")
