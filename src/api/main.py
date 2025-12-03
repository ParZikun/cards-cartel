import os
import logging
import asyncio
import json
import httpx
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from database import main as db
from sqlalchemy import desc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Alt Data Logic ---
GRAPHQL_URL = "https://alt-platform-server.production.internal.onlyalt.com/graphql/"
# NOTE: These should be in environment variables
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
COOKIE = os.getenv("COOKIE")

BLACKLISTED_KEYWORDS = ['black star', 'sticker', 'stickers']
ALT_CONCURRENCY_LIMIT = 3 # Limit concurrent requests to avoid rate limiting

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

async def get_asset_id_async(client, cert_id, retries=3, initial_delay=1.0):
    payload = {
        "operationName": "Cert",
        "variables": {"certNumber": cert_id},
        "query": "query Cert($certNumber: String!) { cert(certNumber: $certNumber) { asset { id name __typename } __typename } }"
    }
    delay = initial_delay
    for attempt in range(retries):
        try:
            logger.info(f"Fetching Asset ID for Cert: {cert_id} (Attempt {attempt+1}/{retries})")
            response = await client.post(url=GRAPHQL_URL, json=payload)
            
            if response.status_code != 200:
                logger.warning(f"Alt Asset ID fetch failed for {cert_id}. Status: {response.status_code}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                return None
                
            data = response.json()
            asset = data.get('data', {}).get('cert', {}).get('asset')
            
            if asset and 'id' in asset:
                logger.info(f"Found Asset ID for {cert_id}: {asset['id']}")
                return asset['id']
            else:
                 # If not found, it's likely not on Alt, so don't retry endlessly
                 logger.warning(f"Alt Asset ID not found in response for {cert_id}.")
                 return None
                 
        except Exception as e:
            logger.error(f"Error fetching asset ID for {cert_id}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
    return None

async def get_alt_data_async(client, cert_id, grade, company, retries=3, initial_delay=1.0):
    if not AUTH_TOKEN or not COOKIE:
        logger.error("Missing AUTH_TOKEN or COOKIE environment variables.")
        return None

    asset_id = await get_asset_id_async(client, cert_id)
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
    
    details_payload = {
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
            logger.info(f"Fetching Details & Transactions for Asset ID: {asset_id} (Attempt {attempt+1}/{retries})")
            
            # Add a small random jitter to avoid thundering herd if multiple retries happen
            await asyncio.sleep(0.1 * attempt) 

            details_response, trans_response = await asyncio.gather(
                client.post(url=GRAPHQL_URL, json=details_payload),
                client.post(url=GRAPHQL_URL, json=trans_payload)
            )

            if details_response.status_code != 200 or trans_response.status_code != 200:
                 logger.warning(f"Alt Data fetch failed. Status: {details_response.status_code}/{trans_response.status_code}")
                 if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                 return None

            details_data = details_response.json().get('data', {}).get('asset', {}) or {}
            transactions = trans_response.json().get('data', {}).get('asset', {}).get('marketTransactions', [])

            alt_value_info = details_data.get('altValueInfo', {}) or {}
            confidence_data = alt_value_info.get('confidenceData', {}) or {}
            
            supply = 0
            for pop in details_data.get('cardPops', []):
                if pop.get('gradingCompany') == company and str(pop.get('gradeNumber')) == f"{float(grade):.1f}":
                    supply = pop.get('count', 0)
                    break

            avg_price = 0.0
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
                "alt_value": alt_value_info.get('currentAltValue') or 0.0,
                "avg_price": avg_price,
                "supply": supply,
                "lower_bound": confidence_data.get('currentErrorLowerBound') or 0.0,
                "upper_bound": confidence_data.get('currentErrorUpperBound') or 0.0,
                "confidence": confidence_data.get('currentConfidenceMetric') or 0.0
            }
        except Exception as e:
            logger.error(f"Error fetching Alt data (Attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
    return None

app = FastAPI(title="Cards Cartel API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    logger.info("Initializing Database...")
    db.init_db()
    
    if "internal.onlyalt.com" in GRAPHQL_URL:
        logger.warning(f"WARNING: Using internal Alt URL: {GRAPHQL_URL}. This may not be reachable locally.")

@app.get("/")
def read_root():
    return {"status": "online", "service": "Cards Cartel API"}

@app.get("/api/get-all-deals")
def get_all_deals(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("listed_at", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    Get paginated listings from the database (Admin Page).
    Matches Azure Function: get-all-deals
    """
    offset = (page - 1) * limit
    
    with db.get_session() as session:
        query = session.query(db.Listing) # No filter, get everything
        
        # Sorting
        if sort_by == "price":
            sort_col = db.Listing.price_amount
        elif sort_by == "diff":
            sort_col = db.Listing.alt_value 
        else:
            sort_col = db.Listing.listed_at

        if order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())
            
        # Pagination
        total = query.count()
        listings = query.offset(offset).limit(limit).all()
        
        return {
            "data": [l.__dict__ for l in listings],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        }

@app.get("/api/get-listings")
def get_listings(limit: int = Query(50, le=100)):
    """
    Get active 'Cartel Deals' (AUTOBUY, GOOD, OK).
    Matches Azure Function: get-listings
    """
    deals = db.get_active_deals_by_category(['AUTOBUY', 'GOOD', 'OK'], limit=limit)
    return deals

@app.get("/api/get-wallet-holdings")
async def get_wallet_holdings(
    wallet: str = Query(..., description="Wallet address to fetch holdings for"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Get current holdings for a specific wallet.
    Fetches tokens from Magic Eden and enriches with Alt Data.
    """
    try:
        # 1. Fetch Tokens from Magic Eden (Paginated)
        me_url = f"https://api-mainnet.magiceden.dev/v2/wallets/{wallet}/tokens"
        
        attributes_filter = [
            [{"traitType": "Category", "value": "Pokemon"}],
            [
                {"traitType": "Grading Company", "value": "PSA"},
                {"traitType": "Grading Company", "value": "Beckett"},
                {"traitType": "Grading Company", "value": "BGS"},
                {"traitType": "Grading Company", "value": "CGC"} 
            ]
        ]
        
        params = {
            "collection_symbol": "collector_crypt",
            "limit": limit,
            "offset": offset,
            "attributes": json.dumps(attributes_filter)
        }
        
        headers = {"accept": "application/json"}
        
        # Use requests for synchronous ME call
        response = requests.get(me_url, params=params, headers=headers)
        response.raise_for_status()
        tokens = response.json()
        
        # 2. Prepare for Async Alt Data Fetch
        alt_data_map = {}
        semaphore = asyncio.Semaphore(ALT_CONCURRENCY_LIMIT)

        async def fetch_with_semaphore(client, mint, cert_id, grade, company):
            async with semaphore:
                # Add a small delay before each request to be polite/avoid rate limits
                await asyncio.sleep(0.5) 
                res = await get_alt_data_async(client, cert_id, grade, company)
                return mint, res
        
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client: # Increased timeout
            tasks = []
            
            for token in tokens:
                mint = token.get('mintAddress')
                name = token.get('name', '')
                
                # Blacklist check
                if any(keyword in name.lower() for keyword in BLACKLISTED_KEYWORDS):
                    continue
                
                attributes = token.get('attributes', [])
                
                def get_attr(attrs, trait):
                    for a in attrs:
                        if a.get('trait_type') == trait:
                            return a.get('value')
                    return None
                
                cert_id = get_attr(attributes, "Grading ID")
                grade_raw = get_attr(attributes, "GradeNum")
                company = get_attr(attributes, "Grading Company")
                
                if cert_id and grade_raw and company:
                    # Skip CGC as Alt doesn't support it
                    if company.upper() == "CGC":
                        continue

                    try:
                        grade = float(grade_raw)
                        tasks.append(fetch_with_semaphore(client, mint, cert_id, grade, company))
                    except ValueError:
                        pass
                else:
                    logger.warning(f"Missing Alt data params for mint {mint}")

            if tasks:
                results = await asyncio.gather(*tasks)
                for mint, res in results:
                    if res:
                        alt_data_map[mint] = res
                    else:
                         logger.warning(f"Failed to fetch Alt data for mint {mint}")

        # 3. Format Response
        formatted_tokens = []
        for token in tokens:
            mint = token.get('mintAddress')
            name = token.get('name', '')
            
            # Blacklist check (again, to filter output)
            if any(keyword in name.lower() for keyword in BLACKLISTED_KEYWORDS):
                continue

            attributes = token.get('attributes', [])
            
            def get_attr(attrs, trait):
                for a in attrs:
                    if a.get('trait_type') == trait:
                        return a.get('value')
                return None

            # Extract all fields requested
            img_url = token.get('image')
            token_mint = mint
            
            grade_num_str = get_attr(attributes, "GradeNum")
            grade_num = float(grade_num_str) if grade_num_str else None
            
            grade = get_attr(attributes, "The Grade")
            category = get_attr(attributes, "Category")
            
            insured_value_str = get_attr(attributes, "Insured Value")
            insured_value = float(insured_value_str) if insured_value_str else None
            
            grading_company = get_attr(attributes, "Grading Company")
            grading_id = get_attr(attributes, "Grading ID")
            
            # Price info
            price_amount = token.get('price')
            price_currency = "SOL" # Default for ME
            
            # Listing status
            is_listed = token.get('listStatus') == 'listed'
            
            # Alt Data
            a_data = alt_data_map.get(mint, {})
            alt_value = a_data.get('alt_value')
            avg_price = a_data.get('avg_price')
            supply = a_data.get('supply')
            alt_asset_id = a_data.get('alt_asset_id')
            alt_value_lower_bound = a_data.get('lower_bound')
            alt_value_upper_bound = a_data.get('upper_bound')
            alt_value_confidence = a_data.get('confidence')
            
            # Calculate Difference (Alt Value - List Price)
            diff = 0.0
            if price_amount and alt_value:
                diff = alt_value - price_amount

            formatted_tokens.append({
                "listing_id": f"sol-{token_mint}", # Generate a pseudo ID
                "name": name,
                "grade_num": grade_num,
                "grade": grade,
                "category": category,
                "insured_value": insured_value,
                "grading_company": grading_company,
                "img_url": img_url,
                "grading_id": grading_id,
                "token_mint": token_mint,
                "price_amount": price_amount,
                "price_currency": price_currency,
                "listed_at": None, # Not available in this endpoint
                "alt_value": alt_value,
                "avg_price": avg_price,
                "supply": supply,
                "alt_asset_id": alt_asset_id,
                "alt_value_lower_bound": alt_value_lower_bound,
                "alt_value_upper_bound": alt_value_upper_bound,
                "alt_value_confidence": alt_value_confidence,
                "cartel_category": "HOLDING", # Updated to HOLDING
                "is_listed": is_listed,
                "last_analyzed_at": datetime.now().isoformat(),
                "diff": diff # Extra field for frontend convenience
            })

        return {
            "wallet": wallet,
            "tokens": formatted_tokens,
            "count": len(formatted_tokens),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error fetching wallet holdings: {e}")
        return {"wallet": wallet, "tokens": [], "error": str(e)}

@app.get("/api/events")
async def sse_endpoint(request: Request):
    """
    Server-Sent Events (SSE) endpoint for real-time updates.
    Polls the database for new 'Cartel Deals'.
    """
    async def event_generator():
        last_check = None
        while True:
            if await request.is_disconnected():
                logger.info("Client disconnected from SSE")
                break

            try:
                # Poll for active deals (AUTOBUY, GOOD, OK)
                # In a real scenario, we might want to track 'last_updated' timestamp
                # For now, we just push the top 10 active deals every 5 seconds
                # to keep the frontend in sync.
                deals = db.get_active_deals_by_category(['AUTOBUY', 'GOOD', 'OK'], limit=10)
                
                if deals:
                    yield {
                        "event": "update",
                        "data": json.dumps(deals)
                    }
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in SSE generator: {e}")
                await asyncio.sleep(5)

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
