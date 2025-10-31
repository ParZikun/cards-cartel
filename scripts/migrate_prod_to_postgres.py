
import sqlite3
from datetime import datetime, timedelta
import logging
import os
import sys
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the project's root directory to the Python path to find the 'src' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.local'))

from src.database.main import engine, Listing, Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
PROD_DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'prod-listings.db')

def fetch_prod_listings():
    """Fetches all listings from the production SQLite database."""
    logger.info(f"Connecting to production database: {PROD_DB_FILE}")
    conn = sqlite3.connect(PROD_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings")
    rows = cursor.fetchall()
    conn.close()
    logger.info(f"Fetched {len(rows)} listings from {PROD_DB_FILE}")
    return [dict(row) for row in rows]

def migrate_data():
    """Migrates data from SQLite to PostgreSQL."""
    # 1. Fetch data from production SQLite DB
    prod_listings = fetch_prod_listings()

    # 2. Prepare data for PostgreSQL
    listings_to_insert = []
    stale_date = datetime.utcnow() - timedelta(days=400)
    
    for listing in prod_listings:
        # Mark as stale
        listing['last_analyzed_at'] = stale_date
        listings_to_insert.append(listing)

    # 3. Connect to PostgreSQL and bulk insert
    logger.info("Connecting to PostgreSQL...")
    Base.metadata.create_all(engine)  # Ensure the table exists
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        logger.info(f"Starting bulk insert of {len(listings_to_insert)} listings...")
        # SQLAlchemy's bulk_insert_mappings is efficient for large inserts
        session.bulk_insert_mappings(Listing, listings_to_insert)  # type: ignore
        session.commit()
        logger.info("Bulk insert completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during bulk insert: {e}")
        session.rollback()
    finally:
        session.close()
        logger.info("PostgreSQL session closed.")

if __name__ == "__main__":
    logger.info("Starting production data migration to PostgreSQL.")
    migrate_data()
    logger.info("Migration script finished.")
