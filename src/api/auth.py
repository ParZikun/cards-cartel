import os
import logging
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import base58
import base64

# --- Configuration ---
# Use a strong secret key in production!
SECRET_KEY = os.getenv("SECRET_KEY", "UNSAFE_DEFAULT_KEY_PLEASE_CHANGE")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_solana_signature(wallet_address: str, message: str, signature: str) -> bool:
    """
    Verifies that the message was signed by the private key corresponding to the wallet address.
    
    Args:
        wallet_address: Base58 encoded public key (the wallet address).
        message: The message that was signed.
        signature: Base58 encoded signature.
    """
    try:
        # Decode the public key (wallet address) from Base58
        pubkey_bytes = base58.b58decode(wallet_address)
        
        # Decode the signature from Base58 (Phantom returns Base58)
        signature_bytes = base58.b58decode(signature)
        
        # Create a VerifyKey object
        verify_key = VerifyKey(pubkey_bytes)
        
        # Verify the signature
        # We need to verify the bytes of the message
        message_bytes = message.encode()
        
        verify_key.verify(message_bytes, signature_bytes)
        return True
    except (ValueError, BadSignatureError, Exception) as e:
        logger.warning(f"Signature verification failed for {wallet_address}: {e}")
        return False

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        wallet_address: str = payload.get("sub")
        if wallet_address is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    return wallet_address
