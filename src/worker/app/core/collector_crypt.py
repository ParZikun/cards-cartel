import httpx
import logging
import re

logger = logging.getLogger(__name__)

# Use the same shared client style as utils if possible, or new one
async_client = httpx.AsyncClient(timeout=5, follow_redirects=True)

async def fetch_cc_metadata(mint_address: str) -> dict | None:
    """
    Fetches metadata from Collector Crypt for a given mint address using their public API.
    Returns None if page not found or parsing fails.
    """
    if not mint_address: return None
    
    url = f"https://api.collectorcrypt.com/cards/publicNft/{mint_address}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://collectorcrypt.com/',
        'Origin': 'https://collectorcrypt.com'
    }
    
    try:
        response = await async_client.get(url, headers=headers)
        
        if response.status_code == 404:
            logger.warning(f"CC Verification: Mint {mint_address} not found via API.")
            return None
            
        if response.status_code != 200:
            logger.warning(f"CC API Error {response.status_code}: {response.text}")
            return None
            
        data = response.json()
        item_name = data.get('itemName')
        
        if not item_name:
            logger.warning(f"CC Verification: No itemName found in API response for {mint_address}")
            return None
            
        logger.debug(f"CC Item Name: {item_name}")
        
        # Parse Item Name Logic (Same as before)
        # Format: "2023 #051 SNORLAX PSA 9 POKEMON..."
        
        # 1. Company
        company = "Unknown"
        if "PSA" in item_name: company = "PSA"
        elif "BGS" in item_name or "BECKETT" in item_name: company = "BGS"
        elif "CGC" in item_name: company = "CGC"
        
        # 2. Grade
        grade_num = None
        match_grade = re.search(r'(PSA|BGS|CGC)\s+(\d+(\.\d+)?)', item_name)
        if match_grade:
            grade_num = float(match_grade.group(2))
            if company == "Unknown": company = match_grade.group(1)
        
        return {
            'title': item_name,
            'company': company,
            'grade': grade_num,
            'url': f"https://collectorcrypt.com/assets/solana/{mint_address}"
        }

    except Exception as e:
        logger.error(f"CC Verification Error for {mint_address}: {e}")
        return None

def verify_match(me_data: dict, cc_data: dict) -> tuple[bool, str]:
    """
    Compares Magic Eden data with Collector Crypt data.
    Returns (True, "Match") or (False, "Reason").
    """
    if not cc_data:
        # If API fails/404s, we can't verify. 
        # Strategy: Allow undetermined? or Block?
        # User requested rigorous verification.
        # But if API is down, we stop buying? 
        # Creating a "Soft Fail" -> Undetermined would be safer than blocking everything if API hiccups.
        return False, "CC Data Not Found"
        
    # 1. Company Check
    me_company = me_data.get('grading_company', '').upper()
    cc_company = cc_data.get('company', '').upper()
    
    # Normalizing
    if me_company == "BECKETT": me_company = "BGS"
    if cc_company == "BECKETT": cc_company = "BGS"

    if me_company != cc_company:
         return False, f"Company Mismatch: ME={me_company} vs CC={cc_company}"
         
    # 2. Grade Check
    try:
        me_grade = float(me_data.get('grade_num', 0))
        cc_grade = float(cc_data.get('grade', 0))
        
        if me_grade != cc_grade:
            return False, f"Grade Mismatch: ME={me_grade} vs CC={cc_grade}"
            
    except (ValueError, TypeError):
        return False, "Invalid Grade Format"
        
    return True, "Match"
