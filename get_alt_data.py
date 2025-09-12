import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

def get_asset_market_transactions(asset_id: str, grade: str, company: str):
    """Fetches and cleans recent market transactions for a specific asset."""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    payload = {
        "operationName": "AssetMarketTransactionsWithTimeSeriesData",
        "variables": {
            "id": asset_id,
            "marketTransactionFilter": {"gradingCompany": company, "gradeNumber": f"{float(grade):.1f}", "allGrades": False},
            "tsFilter": {"autograph": None, "endDate": end_date, "gradeNumber": f"{float(grade):.1f}", "gradingCompany": company, "startDate": start_date}
        },
        "query": "query AssetMarketTransactionsWithTimeSeriesData($id: ID!, $marketTransactionFilter: MarketTransactionFilter!, $tsFilter: TimeSeriesFilter!) { asset(id: $id) { pricingData( marketTransactionFilter: $marketTransactionFilter tsFilter: $tsFilter ) { marketTransactions { id date price __typename } __typename } __typename } }"
    }
    
    try:
        response = requests.post(url=GRAPHQL_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()
        
        transactions = data.get('data', {}).get('asset', {}).get('pricingData', {}).get('marketTransactions', [])
        return transactions
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: API call to get market transactions failed for asset '{asset_id}': {e}")
        return None

def get_transactions(cert_id: str, grade: str, company: str):
    """
    Main function to orchestrate the process of getting transactions for a given cert ID.
    This is the function you will call from other files.
    """
    asset_id = CERT_ID_TO_ASSET_ID_CACHE.get(cert_id)
    
    if not asset_id:
        print(f"CACHE MISS: Looking up asset_id for cert '{cert_id}'...")
        asset_id = get_asset_id(cert_id)
        if asset_id:
            CERT_ID_TO_ASSET_ID_CACHE[cert_id] = asset_id
            print(f"SUCCESS: Found asset_id '{asset_id}'. Storing in cache.")
        else:
            return None
    else:
        print(f"CACHE HIT: Found asset_id '{asset_id}' for cert '{cert_id}'.")

    transactions = get_asset_market_transactions(asset_id, grade, company)
    return transactions

# --- SANITY TEST ---
# This block runs only when you execute this file directly (e.g., "python get_alt_data.py")
if __name__ == "__main__":
    # Example card details you'd get from a Magic Eden listing
    example_cert_id = "53030514" # ME - GRADING ID
    example_grade = "10"         # ME - GRADE NUM 
    example_company = "PSA"      # ME - GRADING COMPANY
    
    print("--- Running Standalone Test ---")
    all_transactions = get_transactions(example_cert_id, example_grade, example_company)
    
    if all_transactions:
        print(f"\nSuccessfully fetched {len(all_transactions)} transactions.")
        for tx in all_transactions[:5]:
            price_value = float(tx['price'])
            print(f"  - Date: {tx['date']}, Price: ${price_value:.2f}")
    else:
        print("\nCould not fetch transactions for the given card.")