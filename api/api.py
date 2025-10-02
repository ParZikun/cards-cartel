import sqlite3
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# --- Basic Configuration ---
DATABASE_PATH = 'listings.db' # This path will be mapped by Docker Compose

# --- Setup Logging ---
# This provides clean, informative logs for our API's activity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Initialize Flask App ---
app = Flask(__name__)

# --- Enable CORS (Cross-Origin Resource Sharing) ---
# This is a CRITICAL step. It allows your frontend (hosted on Vercel)
# to make requests to your API (hosted on Azure) without being
# blocked by browser security policies.
CORS(app)

def get_db_connection():
    """
    Establishes a connection to the SQLite database.
    Configures the connection to return rows that can be accessed by column name.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        # This line is key: it makes rows behave like dictionaries
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection failed: {e}")
        return None

# --- API Endpoint Definition ---
@app.route('/api/listings', methods=['GET'])
def get_listings():
    """
    The main API endpoint to fetch the 200 most recently added listings.
    """
    logger.info("Request received for /api/listings")
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Could not connect to the database"}), 500

    try:
        cursor = conn.cursor()
        # Fetch the 200 most recent entries by their insertion order (rowid)
        cursor.execute("SELECT * FROM listings ORDER BY rowid DESC LIMIT 200")
        listings = cursor.fetchall()
        conn.close()
        
        # Convert the sqlite3.Row objects into a list of standard dictionaries
        listings_dict = [dict(row) for row in listings]
        
        logger.info(f"Successfully fetched and returned {len(listings_dict)} listings.")
        return jsonify(listings_dict)

    except Exception as e:
        logger.error(f"An error occurred while fetching listings: {e}", exc_info=True)
        if conn:
            conn.close()
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Main Execution Block ---
if __name__ == '__main__':
    # 'host="0.0.0.0"' is essential for running inside a Docker container.
    # It tells the app to listen on all available network interfaces.
    app.run(host='0.0.0.0', port=5000, debug=True)
