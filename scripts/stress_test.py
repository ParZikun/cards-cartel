import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Set DRY RUN mode for safety
os.environ["DRY_RUN"] = "true"

from worker.app.core import processor

# --- MOCK DATA GENERATOR ---
def create_mock_listing(name, price, category="Pokemon", company="PSA", mint="mock_mint"):
    return {
        'listing_id': f"list_{mint}",
        'name': name,
        'category': category,
        'grading_company': company,
        'grading_id': '123456',
        'grade_num': 10,
        'price_amount': price,
        'price_currency': 'SOL',
        'token_mint': mint,
        'seller': 'mock_seller',
        'attributes': []
    }

def create_mock_alt_response(alt_value, confidence, name="Mock Card"):
    return {
        'alt_asset_id': 'alt_123',
        'alt_name': name,
        'alt_value': alt_value,
        'avg_price': alt_value,
        'supply': 10,
        'lower_bound': alt_value * 0.9,
        'upper_bound': alt_value * 1.1,
        'confidence': confidence
    }

# --- TEST SCENARIOS ---
SCENARIOS = [
    {
        "name": "🚫 1. Invalid Category (Magic)",
        "listing": create_mock_listing("Black Lotus", 100, category="Magic"),
        "alt_price": 0, "conf": 0,
        "expected": "SKIP"
    },
    {
        "name": "🚫 2. Invalid Company (CGC)",
        "listing": create_mock_listing("Charizard", 100, company="CGC"),
        "alt_price": 0, "conf": 0,
        "expected": "SKIP"
    },
    {
        "name": "🔵 3. BLUE Deal (-16%)",
        "listing": create_mock_listing("Pikachu", 84), # 84 vs 100 = -16%
        "alt_price": 100, "conf": 90,
        "expected": "OK" # INFO Alert
    },
    {
        "name": "🔴 4. RED Deal (-25%)",
        "listing": create_mock_listing("Mewtwo", 75), # 75 vs 100 = -25%
        "alt_price": 100, "conf": 90,
        "expected": "GOOD" # HIGH Alert
    },
    {
        "name": "🟡 5. GOLD Deal (High Discount, Low Conf)",
        "listing": create_mock_listing("Lugia", 50), # 50 vs 100 = -50%
        "alt_price": 100, "conf": 60, # Conf < 75
        "expected": "GOLD" # GOLD Alert
    },
    {
        "name": "⚡ 6. AUTOBUY (High Discount, High Conf)",
        "listing": create_mock_listing("Rayquaza", 50), # 50 vs 100 = -50%
        "alt_price": 100, "conf": 80, # Conf > 75
        "expected": "AUTOBUY"
    },
    {
        "name": "🍯 7. HONEYPOT (-90%)",
        "listing": create_mock_listing("Gengar", 10), # 10 vs 100 = -90%
        "alt_price": 100, "conf": 90,
        "expected": "SUSPICIOUS" # Cap Hit
    }
]

# --- ASYNC MOCK HELPER ---
async def async_return(result):
    return result

async def run_tests():
    logger.info("🧪 STARTING STRESS TEST SIMULATION...")
    logger.info("------------------------------------------------")
    
    queue = asyncio.Queue()
    
    # --- MOCKS ---
    # Mock Database Calls
    with patch('worker.app.core.processor.database') as mock_db:
        # Mock eligible buyers for Autobuy
        mock_db.get_eligible_buyers.return_value = [{
            'user_wallet': 'User1_Wallet',
            'priority': 1,
            'encrypted_private_key': 'key',
            'discord_id': '123456789', # MOCKED DB ID
            'rpc_endpoint': 'https://mock.rpc'
        }]
        
        # Mock Collector Crypt (Always Match)
        with patch('worker.app.core.processor.cc') as mock_cc:
            # FIX: Return Awaitable
            mock_cc.fetch_cc_metadata.side_effect = lambda *args, **kwargs: async_return({'title': 'Mock Title'})
            mock_cc.verify_match.return_value = (True, "Matched") # Not awaited in gathered task, wait. verify_match is sync?
            # Checking processor.py: verify_match is called AFTER gather. fetch_cc_metadata IS awaited (gathered).
            
            # Mock Alt Data (Dynamic per scenario)
            with patch('worker.app.core.processor.alt') as mock_alt:
                
                # Mock Utils (Price Config)
                with patch('worker.app.core.processor.utils') as mock_utils:
                    # Mock 1 SOL = 100 USD (Simple Math)
                    def mock_price_conv(amount, currency):
                        return {'price_usdc': amount, 'price_sol': amount} # 1:1 for simplicity
                    
                    mock_utils.get_price_in_both_currencies.side_effect = lambda *args, **kwargs: async_return(mock_price_conv(*args, *kwargs))

                    # --- RUN LOOP ---
                    for scenario in SCENARIOS:
                        logger.info(f"\\n▶️ Running: {scenario['name']}")
                        
                        # Setup Alt Mock (FIX: Return Awaitable)
                        mock_resp = create_mock_alt_response(
                            scenario['alt_price'], 
                            scenario['conf'], 
                            name=scenario['listing']['name']
                        )
                        mock_alt.get_alt_data_async.side_effect = lambda *args, **kwargs: async_return(mock_resp)
                        
                        # RUN PROCESSOR
                        result, category = await processor.process_listing(
                            scenario['listing'], 
                            queue=queue, 
                            fast_mode=True
                        )
                        
                        # VERIFY
                        success = (category == scenario['expected'])
                        icon = "✅" if success else "❌"
                        logger.info(f"   Result: {category} | Expected: {scenario['expected']} | {icon}")
                        
                        # Check Queue Logic (Notification Payload)
                        if not queue.empty():
                            payload = await queue.get()
                            level = payload.get('alert_level')
                            b_broadcast = payload.get('broadcast_admins')
                            t_discord = payload.get('target_discord_id')
                            
                            logger.info(f"   📩 Notification: Level={level} | Broadcast={b_broadcast} | Target={t_discord}")
                            
                            if category == 'AUTOBUY':
                                if t_discord == '123456789' and b_broadcast is True:
                                    logger.info("   🎯 AUTOBUY Logic Verified: User DM + Admin Broadcast set.")
                                else:
                                    logger.error("   ⚠️ AUTOBUY Logic Fail: Missing DM flags.")

    logger.info("\n------------------------------------------------")
    logger.info("🏁 Stress Test Complete.")

if __name__ == "__main__":
    asyncio.run(run_tests())
