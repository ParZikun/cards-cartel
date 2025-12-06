import os
import logging
import asyncio
import json
import httpx
import requests
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from fastapi import FastAPI, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from database import main as db
from sqlalchemy import desc
from worker.app.core import syncer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Alt Data Logic ---
GRAPHQL_URL = "https://alt-platform-server.production.internal.onlyalt.com/graphql/"
# NOTE: These should be in environment variables
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
COOKIE = os.getenv("COOKIE")
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

def get_cached_alt_data(signature_id: str):
    """Checks DB for cached Alt Valuation data < 24h old."""
    try:
        with db.get_session() as session:
            valuation = session.query(db.AltValuation).filter(db.AltValuation.signature_id == signature_id).first()
            if valuation:
                # Check freshness (e.g., 24 hours)
                # Use timezone-aware comparison
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                
                last_updated = valuation.last_updated_at
                # Handle case where DB returns naive (though it should be aware if column is DateTime(timezone=True))
                if last_updated and last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)

                if last_updated and last_updated >= cutoff:
                    logger.info(f"Cache HIT for {signature_id}")
                    return {
                        "alt_asset_id": valuation.alt_asset_id,
                        "alt_value": valuation.alt_value,
                        "avg_price": 0.0, # Not storing historical avg in this table yet, simple caching
                        "supply": 0,      # Not storing supply yet
                        "lower_bound": valuation.alt_value_min,
                        "upper_bound": valuation.alt_value_max,
                        "confidence": valuation.confidence
                    }
                else:
                    logger.info(f"Cache STALE for {signature_id}")
            else:
                logger.info(f"Cache MISS for {signature_id}")
    except Exception as e:
        logger.error(f"Error reading Alt Cache: {e}")
    return None

def cache_alt_data(signature_id: str, data: dict):
    """Saves Alt Valuation data to DB."""
    try:
        with db.get_session() as session:
            # Upsert
            stmt = db.insert(db.AltValuation).values(
                signature_id=signature_id,
                alt_asset_id=data.get('alt_asset_id'),
                alt_value=data.get('alt_value'),
                alt_value_min=data.get('lower_bound'),
                alt_value_max=data.get('upper_bound'),
                confidence=data.get('confidence'),
                last_updated_at=datetime.utcnow()
            )
            update_dict = {
                "alt_value": stmt.excluded.alt_value,
                "alt_value_min": stmt.excluded.alt_value_min,
                "alt_value_max": stmt.excluded.alt_value_max,
                "confidence": stmt.excluded.confidence,
                "last_updated_at": datetime.utcnow()
            }
            # PostgreSQL On Conflict Update
            stmt = stmt.on_conflict_do_update(
                index_elements=['signature_id'],
                set_=update_dict
            )
            session.execute(stmt)
            session.commit()
            logger.info(f"Cached Alt data for {signature_id}")
    except Exception as e:
        logger.error(f"Error caching Alt data: {e}")

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
            [{"traitType": "Category", "value": "Pokemon"}]
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

        async def fetch_with_semaphore(client, mint, cert_id, grade, company, signature_id):
            async with semaphore:
                # Add a small delay before each request to be polite/avoid rate limits
                await asyncio.sleep(0.3) 
                
                # Double-check cache inside worker just in case? No, outer check is enough for now.
                
                res = await get_alt_data_async(client, cert_id, grade, company)
                
                if res:
                    # Cache the result!
                    cache_alt_data(signature_id, res)
                    
                return mint, res
        
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client: # Increased timeout
            tasks = []
            
            for token in tokens:
                mint = token.get('mintAddress')
                name = token.get('name', '')
                
                attributes = token.get('attributes', [])
                
                def get_attr(attrs, trait):
                    for a in attrs:
                        if a.get('trait_type') == trait:
                            return a.get('value')
                    return None
                
                cert_id = get_attr(attributes, "Grading ID")
                grade_raw = get_attr(attributes, "GradeNum")
                grade_str_attr = get_attr(attributes, "The Grade") # Get the string representation
                company = get_attr(attributes, "Grading Company")
                
                if cert_id and grade_raw and company:
                    # Normalize Company Name for Alt
                    company_upper = company.upper()
                    if "BECKETT" in company_upper or "BGS" in company_upper:
                        company = "BGS"
                    elif "PSA" in company_upper:
                        company = "PSA"
                    elif "SGC" in company_upper:
                        company = "SGC"
                    elif "CGC" in company_upper:
                        company = "CGC"
                        
                    # Skip CGC as Alt doesn't support it
                    if company == "CGC":
                        continue

                    try:
                        grade = float(grade_raw)
                        
                        # --- Grade Verification from Attribute String ---
                        # Verify with "The Grade" string using regex
                        if grade_str_attr:
                             grade_match = re.search(r"(\d+(?:\.\d+)?)", str(grade_str_attr))
                             if grade_match:
                                 try:
                                     grade_from_str = float(grade_match.group(1))
                                     if grade_from_str != grade:
                                         logger.debug(f"Grade mismatch for {name}: Attr String '{grade_str_attr}' says {grade_from_str}, GradeNum says {grade}. Using String.")
                                         grade = grade_from_str
                                 except ValueError:
                                     pass
                        # ------------------------------------
                        
                        # CACHE CHECK
                        signature_id = f"{company}_{grade}_{cert_id}"
                        cached_data = get_cached_alt_data(signature_id)
                        
                        if cached_data:
                            alt_data_map[mint] = cached_data
                            # If we have cached data, we might miss 'avg_price' or 'supply' if they aren't in the cache table yet.
                            # For now, this tradeoff is acceptable for speed.
                        else:
                            tasks.append(fetch_with_semaphore(client, mint, cert_id, grade, company, signature_id))
                            
                    except ValueError:
                        pass
                else:
                    pass # logger.warning(f"Missing Alt data params for mint {mint}")

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
                "grading_id": grading_id,
                "name": name,
                "grade_num": grade_num,
                "grade": grade,
                "category": category,
                "insured_value": insured_value,
                "grading_company": grading_company,
                "img_url": img_url,
                "token_mint": token_mint,
                "price_amount": price_amount,
                "price_currency": price_currency,
                "alt_value": alt_value,
                "avg_price": avg_price,
                "supply": supply,
                "alt_asset_id": alt_asset_id,
                "alt_value_lower_bound": alt_value_lower_bound,
                "alt_value_upper_bound": alt_value_upper_bound,
                "alt_value_confidence": alt_value_confidence,
                "cartel_category": "HOLDING",
                "is_listed": is_listed,
                "last_analyzed_at": datetime.now().isoformat(),
                "diff": diff 
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


@app.post("/api/trigger/full-recheck")
async def trigger_full_recheck(background_tasks: BackgroundTasks):
    """
    Triggers a full database sync and recheck in the background.
    """
    logger.info("Received request to trigger full recheck.")
    # We pass None for the queue as the API process doesn't own the Discord bot queue
    background_tasks.add_task(syncer.full_sync, queue=None)
    return {"status": "accepted", "message": "Full recheck started in background."}

@app.post("/api/trigger/recheck")
async def trigger_recheck(request: Request):
    """
    Triggers a recheck of skipped listings for a specific duration.
    Body: {"duration": "1H", "category": "SKIP"} (Category implicit in recheck logic for now)
    Blocking call: Waits for recheck to complete.
    """
    try:
        body = await request.json()
        duration = body.get("duration", "1H")
        
        logger.info(f"Received request to trigger recheck for duration: {duration}")
        # Await the process so the frontend knows when it's done
        new_deals = await syncer.recheck_listings(duration_str=duration, queue=None)
        
        return {"status": "success", "message": f"Recheck for {duration} complete. Found {new_deals} new deals."}
    except Exception as e:
        logger.error(f"Error parsing recheck request: {e}")
        return {"status": "error", "message": str(e)}

# Import processor and magic_eden for inspect functionality
from worker.app.core import processor
from worker.app.core import magic_eden as me

@app.get("/api/inspect-card")
async def inspect_card(query: str = Query(..., description="Mint Address or Grading ID")):
    """
    Inspects a card by Mint Address or Grading ID.
    1. Checks Database.
    2. If found < 24h old, returns DB data.
    3. If not found or stale AND query is a Mint Address:
       - Fetches live from Magic Eden.
       - Processes (fetches Alt data).
       - Updates DB.
       - Returns fresh data.
    4. If Grading ID and not in DB => 404 (Cannot find mint from grading ID efficiently).
    """
    query = query.strip()
    listing = None
    
    # 1. Check Database
    with db.get_session() as session:
        # Search by mint OR grading_id
        # Note: We need exact match for now
        listing_obj = session.query(db.Listing).filter(
            (db.Listing.token_mint == query) | 
            (db.Listing.grading_id == query)
        ).first()
        
        if listing_obj:
            listing = listing_obj.__dict__
            
    # 2. Check Freshness
    is_stale = False
    if listing:
        last_analyzed = listing.get('last_analyzed_at')
        if not last_analyzed:
            is_stale = True
        else:
            if isinstance(last_analyzed, str):
                last_analyzed = datetime.fromisoformat(last_analyzed.replace('Z', '+00:00'))
            if last_analyzed.tzinfo is None:
                last_analyzed = last_analyzed.replace(tzinfo=timezone.utc)
                
            if datetime.now(timezone.utc) - last_analyzed > timedelta(hours=24):
                is_stale = True
    
    # 3. If missing or stale, try Live Update (ONLY if we have a mint address)
    # If we found a stale listing in DB, we have the mint address from it.
    # If we found nothing, we assume the query MIGHT be a mint address.
    
    mint_to_check = None
    if listing:
        mint_to_check = listing.get('token_mint')
    elif len(query) > 30 and " " not in query: # Rudimentary check for potential mint address
        mint_to_check = query
        
    if (not listing or is_stale) and mint_to_check:
        logger.info(f"Inspect: Fetching live data for {mint_to_check}...")
        try:
            # A. Fetch from ME
            card_data = await me.check_listing_status_async(mint_to_check)
            
            if isinstance(card_data, dict) and card_data.get('mintAddress'):
                # B. Construct Listing Object (Partial)
                # We need to map the raw ME response to what 'process_listing' expects (simulating _process_listing from magic_eden.py)
                # Actually, `me.check_listing_status_async` returns raw /v2/tokens/ data which is DIFFERENT from /idxv2/ data structure used in `_process_listing`.
                # We need to adapt it. 
                
                # Check list status
                is_listed = card_data.get('listStatus') == 'listed'
                price = float(card_data.get('price', 0)) if is_listed else 0.0
                
                # Extract Attributes
                attributes = card_data.get('attributes', [])
                def get_val(key):
                    for a in attributes:
                        if a.get('trait_type') == key: return a.get('value')
                    return None
                    
                grading_id = get_val("Grading ID") 
                grading_company = get_val("Grading Company")
                grade_num_str = get_val("GradeNum")
                grade_str = get_val("The Grade")
                
                if grading_id and grading_company:
                    # Normalize logic similar to magic_eden.py
                    company = grading_company
                    if "BECKETT" in company.upper() or "BGS" in company.upper(): company = "BGS"
                    elif "PSA" in company.upper(): company = "PSA"
                        
                    grade_num = float(grade_num_str) if grade_num_str else 0.0
                    
                    listing_input = {
                        'listing_id': "manual_inspect", # Placeholder
                        'name': card_data.get('name'),
                        'grade_num': grade_num,
                        'grade': grade_str or str(grade_num),
                        'category': get_val("Category") or "Card",
                        'insured_value': float(get_val("Insured Value") or 0),
                        'grading_company': company,
                        'img_url': card_data.get('image'),
                        'grading_id': grading_id,
                        'token_mint': mint_to_check,
                        'price_amount': price,
                        'price_currency': 'SOL',
                        'listed_at': datetime.now(timezone.utc).isoformat(), # Approximation
                        # Add fields expected by processor if needed
                    }
                    
                    # C. Process (Enrich with Alt Data + Update DB)
                    # Note: process_listing saves to DB!
                    await processor.process_listing(listing_input, queue=None, send_alert=False)
                    
                    # D. Re-fetch from DB to get the full, clean object
                    with db.get_session() as session:
                        listing_obj = session.query(db.Listing).filter(db.Listing.token_mint == mint_to_check).first()
                        if listing_obj:
                            listing = listing_obj.__dict__
            else:
                logger.warning(f"Inspect: Mint {mint_to_check} not found on ME or invalid.")
                
        except Exception as e:
            logger.error(f"Inspect Live Fetch Error: {e}")
            
    if listing:
        return listing
    else:
        # 404
        return {"error": "Card not found in Database and could not be fetched from Magic Eden (Must provide valid Mint Address for live fetch)."}
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
