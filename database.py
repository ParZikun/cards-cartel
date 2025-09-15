import sqlite3
from datetime import datetime, timezone

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
        avg_sale_price REAL,
        supply INTEGER,
        alt_asset_id TEXT,
        alt_value_lower_bound REAL,
        alt_value_upper_bound REAL,
        alt_value_confidence REAL,
        last_checked_at TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")

def get_listings_without_alt_data():
    """
    Fetches all listings from the DB that have not yet been enriched with ALT data.
    This is used for the initial "catch-up" process.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    cursor = conn.cursor()

    # We check for alt_value being NULL as the indicator that it needs processing
    cursor.execute("SELECT * FROM listings WHERE alt_value IS NULL")
    rows = cursor.fetchall()

    conn.close()
    
    # Convert the list of sqlite3.Row objects to standard dictionaries
    return [dict(row) for row in rows]


def save_listings(listings: list):
    """
    Saves a list of new listing dictionaries from Magic Eden to the database.
    It ignores any listings that already exist based on their primary key (listing_id).
    """
    if not listings:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Prepare data for insertion with NULL placeholders for ALT fields
    data_to_insert = []
    for listing in listings:
        data_to_insert.append((
            listing.get('listing_id'),
            listing.get('name'),
            listing.get('grade'),
            listing.get('grade_num'),
            listing.get('category'),
            listing.get('insured_value'),
            listing.get('grading_company'),
            listing.get('img_url'),
            listing.get('grading_id'),
            listing.get('token_mint'),
            listing.get('price_amount'),
            listing.get('price_currency'),
            listing.get('listed_at')
        ))

    # Use INSERT OR IGNORE to prevent errors if a listing_id is already in the DB
    cursor.executemany("""
    INSERT OR IGNORE INTO listings (listing_id, name, grade, grade_num, category, insured_value, grading_company, img_url, grading_id, token_mint, price_amount, price_currency, listed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_to_insert)
    
    conn.commit()
    conn.close()

def get_all_listing_ids() -> set:
    """
    Retrieves a set of all listing_ids currently stored in the database.
    This is used to initialize the watchdog's state so it doesn't re-process items.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT listing_id FROM listings")
    rows = cursor.fetchall()
    conn.close()
    return {row[0] for row in rows}

def update_listing_alt_data(listing_id: str, alt_data: dict):
    """
    Updates a specific listing with its processed ALT data.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
    UPDATE listings 
    SET 
        alt_asset_id = ?
        alt_value = ?, 
        avg_sale_price = ?, 
        supply = ?, 
        alt_value_lower_bound = ?, 
        alt_value_upper_bound = ?, 
        alt_value_confidence = ?, 
        last_checked_at = ?
    WHERE listing_id = ?
    """, (
        alt_data.get('alt_asset_id'),
        alt_data.get('alt_value'), 
        alt_data.get('avg_price'), 
        alt_data.get('supply'),
        alt_data.get('lower_bound'), 
        alt_data.get('upper_bound'), 
        alt_data.get('confidence'),
        timestamp, 
        listing_id
    ))
    
    conn.commit()
    conn.close()
