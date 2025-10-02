import sqlite3
from datetime import datetime, timezone
from pytz import timezone
import logging

logger = logging.getLogger(__name__)

# --- Configuration ---
DB_FILE = "listings.db"

def init_db():
    """
    Initializes the database and creates the 'listings' table with the final schema.
    This function is safe to run multiple times.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # The complete table schema to hold all data from ME and ALT
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        listing_id TEXT PRIMARY KEY,
        name TEXT,
        grade_num REAL,
        grade TEXT,
        category TEXT,
        insured_value REAL,
        grading_company TEXT,
        img_url TEXT,
        grading_id TEXT,
        token_mint TEXT,
        price_amount REAL,
        price_currency TEXT,
        listed_at TEXT,
        alt_value REAL,
        avg_price REAL,
        supply INTEGER,
        alt_asset_id TEXT,
        alt_value_lower_bound REAL,
        alt_value_upper_bound REAL,
        alt_value_confidence REAL,
        cartel_category TEXT NOT NULL DEFAULT 'NEW'
    )
    """)
    conn.commit()
    conn.close()

def save_listing(listings: list):
    """Saves new listings with a 'NEW' status."""
    if not listings: return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    data_to_insert = [(
        listing.get('listing_id'), listing.get('name'), listing.get('grade'),
        listing.get('grade_num'), listing.get('category'), listing.get('insured_value'),
        listing.get('grading_company'), listing.get('img_url'), listing.get('grading_id'),
        listing.get('token_mint'), listing.get('price_amount'), listing.get('price_currency'),
        listing.get('listed_at')
    ) for listing in listings]
    cursor.executemany("""
    INSERT OR IGNORE INTO listings (
        listing_id, name, grade, grade_num, category, insured_value, grading_company,
        img_url, grading_id, token_mint, price_amount, price_currency, listed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_to_insert)
    conn.commit()
    conn.close()

def update_listing(listing_id: str, alt_data: dict, cartel_category: str):
    """
    Updates an existing listing with its enriched ALT data and final category.
    This is now the single function for updating a processed listing.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE listings SET 
        alt_asset_id = ?, alt_value = ?, avg_price = ?, supply = ?, 
        alt_value_lower_bound = ?, alt_value_upper_bound = ?, alt_value_confidence = ?, 
        cartel_category = ?
    WHERE listing_id = ?
    """, (
        alt_data.get('alt_asset_id'), alt_data.get('alt_value'), alt_data.get('avg_price'),
        alt_data.get('supply'), alt_data.get('lower_bound'), alt_data.get('upper_bound'),
        alt_data.get('confidence'), cartel_category, listing_id
    ))

    conn.commit()
    conn.close()

def skip_listing(listing_id: str, cartel_category: str):
    """
    Updates an existing listing with its enriched ALT data and final category.
    This is now the single function for updating a processed listing.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("UPDATE listings SET cartel_category = ? WHERE listing_id = ?", (cartel_category, listing_id))

    conn.commit()
    conn.close()


def get_unprocessed_listings():
    """Fetches all listings that have status 'NEW'."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE cartel_category = 'NEW'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_listing_ids() -> set:
    """Retrieves all listing_ids from the database to prevent duplicate processing."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT listing_id FROM listings")
    rows = cursor.fetchall()
    conn.close()
    return {row[0] for row in rows}

