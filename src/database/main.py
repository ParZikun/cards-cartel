import os
import logging
from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

# --- Configuration ---
# It is recommended to use environment variables for database credentials
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "cards_cartel")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Model ---
class Listing(Base):
    __tablename__ = "listings"

    listing_id = Column(String, primary_key=True)
    name = Column(String)
    grade_num = Column(Float)
    grade = Column(String)
    category = Column(String)
    insured_value = Column(Float)
    grading_company = Column(String)
    img_url = Column(String)
    grading_id = Column(String)
    token_mint = Column(String)
    price_amount = Column(Float)
    price_currency = Column(String)
    listed_at = Column(String) # Consider using DateTime for this
    alt_value = Column(Float)
    avg_price = Column(Float)
    supply = Column(Integer)
    alt_asset_id = Column(String)
    alt_value_lower_bound = Column(Float)
    alt_value_upper_bound = Column(Float)
    alt_value_confidence = Column(Float)
    cartel_category = Column(String, nullable=False, default='NEW')
    is_listed = Column(Boolean, default=True)
    last_analyzed_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Database Functions ---
def init_db():
    """
    Initializes the database and creates the 'listings' table.
    """
    Base.metadata.create_all(bind=engine)

def get_session():
    """Returns a new session from the session factory."""
    return SessionLocal()

def save_listing(listings: list):
    """Saves new listings with a 'NEW' status."""
    if not listings:
        return
    
    with get_session() as session:
        insert_stmt = insert(Listing).values(listings)
        do_nothing_stmt = insert_stmt.on_conflict_do_nothing(index_elements=['listing_id'])
        session.execute(do_nothing_stmt)
        session.commit()

def update_listing(listing_id: str, alt_data: dict, cartel_category: str):
    """
    Updates an existing listing with its enriched ALT data and final category,
    and updates the last_analyzed_at timestamp.
    """
    with get_session() as session:
        session.query(Listing).filter(Listing.listing_id == listing_id).update({
            "alt_asset_id": alt_data.get('alt_asset_id'),
            "alt_value": alt_data.get('alt_value'),
            "avg_price": alt_data.get('avg_price'),
            "supply": alt_data.get('supply'),
            "alt_value_lower_bound": alt_data.get('lower_bound'),
            "alt_value_upper_bound": alt_data.get('upper_bound'),
            "alt_value_confidence": alt_data.get('confidence'),
            "cartel_category": cartel_category,
            "last_analyzed_at": func.now()
        })
        session.commit()

def skip_listing(listing_id: str, cartel_category: str):
    """
    Updates an existing listing with its enriched ALT data and final category.
    """
    with get_session() as session:
        session.query(Listing).filter(Listing.listing_id == listing_id).update({
            "cartel_category": cartel_category
        })
        session.commit()

def get_unprocessed_listings() -> list[dict]:
    """Fetches all listings that have status 'NEW'."""
    with get_session() as session:
        rows = session.query(Listing).filter(Listing.cartel_category == 'NEW').all()
        return [row.__dict__ for row in rows]

def get_all_listing_ids() -> set:
    """Retrieves all listing_ids from the database."""
    with get_session() as session:
        rows = session.query(Listing.listing_id).all()
        return {row[0] for row in rows}

def get_initial_reaper_queue_items() -> list[str]:
    """Queries the DB for all active, relevant listings to populate the reaper queue."""
    with get_session() as session:
        rows = session.query(Listing.token_mint).filter(Listing.is_listed == True, Listing.cartel_category != 'SKIP').all()
        logger.info(f"Found {len(rows)} items for the initial reaper queue.")
        return [row[0] for row in rows]

def update_listing_status(mint_address: str, is_listed: bool):
    """Updates the is_listed flag for a given listing."""
    with get_session() as session:
        session.query(Listing).filter(Listing.token_mint == mint_address).update({"is_listed": is_listed})
        session.commit()
        logger.info(f"Set is_listed={is_listed} for mint {mint_address}")

def get_active_deals_by_category(categories: list, limit: int = 25) -> list[dict]:
    """
    Fetches active deals for a given list of cartel_categories.
    """
    if not categories:
        return []
    with get_session() as session:
        rows = session.query(Listing.name, Listing.listing_id).filter(
            Listing.is_listed == True,
            Listing.cartel_category.in_(categories)
        ).order_by(Listing.listed_at.desc()).limit(limit).all()
        return [{"name": row[0], "listing_id": row[1]} for row in rows]

def get_listing_by_id(listing_id: str) -> dict | None:
    """
    Fetches all details for a single listing by its ID.
    """
    with get_session() as session:
        row = session.query(Listing).filter(Listing.listing_id == listing_id).first()
        return row.__dict__ if row else None

def get_all_active_listings() -> list[dict]:
    """Fetches all listings that are currently marked as listed."""
    with get_session() as session:
        rows = session.query(Listing).filter(Listing.is_listed == True).all()
        return [row.__dict__ for row in rows]

def get_listing_by_mint(mint_address: str) -> dict | None:
    """Fetches all details for a single listing by its mint address."""
    with get_session() as session:
        row = session.query(Listing).filter(Listing.token_mint == mint_address).first()
        return row.__dict__ if row else None

def get_skipped_listings(since: datetime | None) -> list[dict]:
    """
    Fetches all active listings with 'SKIP' category, optionally filtered by a timestamp.

    Args:
        since (datetime | None): If provided, only returns listings analyzed after this timestamp.
                                 The timestamp should be timezone-aware (UTC).

    Returns:
        list[dict]: A list of listing dictionaries.
    """
    with get_session() as session:
        query = session.query(Listing).filter(
            Listing.is_listed == True,
            Listing.cartel_category == 'SKIP'
        )
        if since:
            query = query.filter(Listing.last_analyzed_at >= since)
        rows = query.all()
        return [row.__dict__ for row in rows]
