import logging
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import os
import requests
from functools import wraps
from waitress import serve
from pythonjsonlogger import jsonlogger
from src.database import main as database

# --- Configuration ---
API_KEY = os.getenv('API_KEY')

# --- Setup Logging ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app)

# --- Security Decorator ---
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not API_KEY:
            logger.error("CRITICAL: API_KEY is not configured on the server.")
            abort(500) # Internal Server Error
            
        key_from_header = request.headers.get('X-API-Key')
        if key_from_header and key_from_header == API_KEY:
            return f(*args, **kwargs)
        else:
            logger.warning(f"Unauthorized access attempt from IP: {request.remote_addr}")
            abort(401) # Unauthorized
    return decorated_function

@app.route('/api/listings', methods=['GET'])
@api_key_required  # Apply the security lock to our endpoint
def get_listings():
    logger.info(f"Request received for /api/listings from {request.remote_addr}")
    try:
        with database.get_session() as session:
            rows = session.query(database.Listing).order_by(database.Listing.listed_at.desc()).limit(200).all()
            listings = [row.__dict__ for row in rows]
            for listing in listings:
                listing.pop('_sa_instance_state', None) # Remove SQLAlchemy internal state
        return jsonify(listings)

    except Exception as e:
        logger.error(f"An error occurred while fetching listings: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/wallets/<wallet_address>/tokens', methods=['GET'])
@api_key_required
def get_wallet_tokens(wallet_address):
    logger.info(f"Request received for /api/wallets/{wallet_address}/tokens from {request.remote_addr}")
    # Basic validation for a Solana address
    if not (32 <= len(wallet_address) <= 44 and wallet_address.isalnum()):
        logger.warning(f"Invalid wallet address format received: {wallet_address}")
        return jsonify({"error": "Invalid wallet address format."}), 400
        
    try:
        # Forward query parameters from the incoming request to the Magic Eden API
        params = request.args.to_dict()
        
        me_api_url = f"https://api-mainnet.magiceden.dev/v2/wallets/{wallet_address}/tokens"
        
        response = requests.get(me_api_url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        return jsonify(response.json())

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred while fetching from Magic Eden: {e}", exc_info=True)
        try:
            # Try to return Magic Eden's JSON error response
            error_json = e.response.json()
            return jsonify(error_json), e.response.status_code
        except ValueError: # Catches JSONDecodeError
            # If Magic Eden returns HTML or other non-JSON error, return it as text
            return e.response.text, e.response.status_code
    except Exception as e:
        logger.error(f"An error occurred while fetching wallet tokens: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # The current default is HTTP:
    serve(app, host="0.0.0.0", port=5000)