import sqlite3
import logging
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import os
from functools import wraps
from waitress import serve

# --- Configuration ---
DATABASE_PATH = 'data/listings.db'
DATA_DIR = 'data'
API_KEY = os.getenv('API_KEY')

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def initialize_database():
    """Ensures the DB file and listings table exist before the first request."""
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                listing_id TEXT PRIMARY KEY, name TEXT, grade_num REAL, grade TEXT,
                category TEXT, insured_value REAL, grading_company TEXT, img_url TEXT,
                grading_id TEXT, token_mint TEXT, price_amount REAL, price_currency TEXT,
                listed_at TEXT, alt_value REAL, avg_price REAL, supply INTEGER,
                alt_asset_id TEXT, alt_value_lower_bound REAL, alt_value_upper_bound REAL,
                alt_value_confidence REAL, cartel_category TEXT NOT NULL DEFAULT 'NEW'
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        # In a real production app, you might want to exit here or have a more robust retry.

@app.before_request
def before_first_request_func():
    # This runs ONCE before the very first request to this process.
    initialize_database()

@app.route('/api/listings', methods=['GET'])
@api_key_required  # Apply the security lock to our endpoint
def get_listings():
    logger.info(f"Request received for /api/listings from {request.remote_addr}")
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM listings ORDER BY listed_at DESC LIMIT 200")
        rows = cursor.fetchall()
        conn.close()
        
        listings = [dict(row) for row in rows]
        return jsonify(listings)

    except Exception as e:
        logger.error(f"An error occurred while fetching listings: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    serve(app, host="0.0.0.0", port=5000)