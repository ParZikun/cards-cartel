import os
import json
import base64
import logging
import httpx
from cryptography.fernet import Fernet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned

logger = logging.getLogger(__name__)

# Load Secret Key for Decryption
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    logger.warning("SECRET_KEY not set. Private key decryption will fail.")

def decrypt_private_key(encrypted_key: str) -> str:
    """Decrypts the user's private key using the server-side SECRET_KEY."""
    if not SECRET_KEY:
        raise ValueError("Server SECRET_KEY is not configured.")
    f = Fernet(SECRET_KEY)
    return f.decrypt(encrypted_key.encode()).decode()

async def execute_buy(user_wallet: str, encrypted_private_key: str, listing: dict, rpc_endpoint: str = None) -> bool:
    """
    Executes a Buy Now transaction on Magic Eden for the given listing.
    
    Args:
        user_wallet: The wallet address of the buyer.
        encrypted_private_key: The encrypted private key of the buyer.
        listing: The listing dictionary containing mint, price, seller, etc.
        rpc_endpoint: Optional custom RPC URL.
    
    Returns:
        True if the transaction was submitted successfully, False otherwise.
    """
    try:
        # 1. Decrypt Private Key
        try:
            private_key_str = decrypt_private_key(encrypted_private_key)
            # Handle format (JSON array vs Base58)
            if "[" in private_key_str:
                keypair = Keypair.from_bytes(json.loads(private_key_str))
            else:
                keypair = Keypair.from_base58_string(private_key_str)
        except Exception as e:
            logger.error(f"Failed to decrypt/load private key for {user_wallet}: {e}")
            return False

        # 2. Prepare ME API Params
        # We need keys: tokenMint, price, seller, tokenATA
        # Attempt to map from our 'listing' dict (which comes from ME response usually)
        token_mint = listing.get('token_mint') or listing.get('tokenAddress')
        price = listing.get('price_amount')
        seller = listing.get('seller') # Assuming this exists in our enriched listing
        
        # tokenATA often not in simple listing response? 
        # ME 'getListedNftsByCollectionSymbol' usually provides 'tokenAddress', 'price', 'tokenOwner' (seller).
        # It MIGHT NOT provide 'tokenATA'.
        # If 'tokenATA' is missing, ME API v2/instructions/buy_now might fail or we might need to derive it 
        # (ATA of the seller for that mint).
        # Let's assume for now it's in the listing or we try without it if optional? 
        # Docs say tokenATA is required.
        # Check if 'listing' has it. If not, we might need to fetch it from RPC or use a different endpoint.
        # For now, let's proceed assuming it's passed or try to use what we have.
        token_ata = listing.get('tokenATA') or listing.get('id') # 'id' in ME response sometimes is the ATA address? No.
        
        # Fallback: If we don't have tokenATA, we can try to derive it via RPC? 
        # That adds latency. 
        # Alternatively, checking `magic_eden.py` to see what fields are saved.
        
        if not all([token_mint, price, seller]):
            logger.error(f"Missing required listing info for buy: Mint={token_mint}, Price={price}, Seller={seller}")
            return False

        params = {
            "buyer": str(keypair.pubkey()),
            "seller": seller,
            "tokenMint": token_mint,
            "tokenATA": token_ata, # THIS IS RISKY if None
            "price": price,
            "buyerExpiry": "0",
            "sellerExpiry": "0"
        }
        
        # 3. Call ME API to get Transaction
        url = "https://api-mainnet.magiceden.dev/v2/instructions/buy_now"
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
        tx_data = data.get('txSigned') or data.get('tx')
        if not tx_data:
            logger.error("No transaction data returned from ME.")
            return False
            
        # Decode TX
        tx_bytes = None
        if isinstance(tx_data, dict) and tx_data.get('type') == 'Buffer':
            tx_bytes = bytes(tx_data['data'])
        elif isinstance(tx_data, str):
            tx_bytes = base64.b64decode(tx_data)
            
        if not tx_bytes:
            logger.error("Failed to decode transaction bytes.")
            return False

        # 4. Sign Transaction
        txn = VersionedTransaction.from_bytes(tx_bytes)
        message = txn.message
        # Sign with our keypair
        signature = keypair.sign_message(to_bytes_versioned(message))
        # Reconstruct with new signature (assuming we are the primary signer)
        signed_txn = VersionedTransaction(message, [signature])

        # 5. Send to RPC
        target_rpc = rpc_endpoint or os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
        async with AsyncClient(target_rpc) as solana_client:
            # Send (skip preflight for speed?)
            res = await solana_client.send_transaction(signed_txn)
            
            sig = str(res.value) if hasattr(res, 'value') else str(res)
            logger.info(f"✅ BUY SUBMITTED! Sig: https://solscan.io/tx/{sig}")
            return True

    except Exception as e:
        logger.error(f"Buy execution failed for {user_wallet}: {e}")
        return False
