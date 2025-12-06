import os
import logging
from datetime import datetime
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

class User(Base):
    __tablename__ = "users"

    wallet_address = Column(String(44), primary_key=True)
    tier = Column(String(10), default='NORMAL') # 'GOLD', 'NORMAL', 'BLOCKED'
    status = Column(String(10), default='ACTIVE') # 'ACTIVE', 'SUSPENDED'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True))

class UserSettings(Base):
    __tablename__ = "user_settings"

    user_wallet = Column(String(44), primary_key=True) # Foreign key to users.wallet_address
    max_price = Column(Float, default=10.0)
    priority_fee = Column(Float, default=0.005)
    slippage = Column(Float, default=1.0)
    auto_buy_enabled = Column(Boolean, default=False)
    
    # New Fields
    rpc_endpoint = Column(String, default="https://api.mainnet-beta.solana.com")
    jito_tip_amount = Column(Float, default=0.001)
    encrypted_private_key = Column(String, nullable=True) # User must set this
    
    # Thresholds
    gold_discount_percent = Column(Integer, default=30)
    red_discount_percent = Column(Integer, default=20)
    blue_discount_percent = Column(Integer, default=10)
    
    push_enabled = Column(Boolean, default=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AltValuation(Base):
    __tablename__ = "alt_valuations"

    # Composite unique key or just a string signature? 
    # Using grading_id (cert number) as the primary key is risky if different companies have same cert but unlikely for our scope.
    # Better to use a composite string or specific columns. 
    # Let's use a "signature_id" string: "{company}_{grade}_{cert_id}" normalized.
    signature_id = Column(String, primary_key=True) 
    
    alt_value = Column(Float)
    alt_value_min = Column(Float)
    alt_value_max = Column(Float)
    confidence = Column(Float)
    alt_asset_id = Column(String)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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

def to_dict(obj):
    """Converts a SQLAlchemy model to a dictionary, excluding internal state."""
    if not obj:
        return None
    return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}

def get_active_deals_by_category(categories: list, limit: int = 25) -> list[dict]:
    """
    Fetches active deals for a given list of cartel_categories.
    """
    if not categories:
        return []
    with get_session() as session:
        rows = session.query(Listing).filter(
            Listing.is_listed == True,
            Listing.cartel_category.in_(categories)
        ).order_by(Listing.listed_at.desc()).limit(limit).all()
        return [to_dict(row) for row in rows]

def get_listing_by_id(listing_id: str) -> dict | None:
    """
    Fetches all details for a single listing by its ID.
    """
    with get_session() as session:
        row = session.query(Listing).filter(Listing.listing_id == listing_id).first()
        return to_dict(row)

def update_listing_details(listing_id: str, payload: dict):
    """
    Updates an existing listing with a dictionary of new values.
    """
    if not payload:
        return
    with get_session() as session:
        session.query(Listing).filter(Listing.listing_id == listing_id).update(payload)
        session.commit()

def get_all_active_listings() -> list[dict]:
    """Fetches all listings that are currently marked as listed."""
    with get_session() as session:
        rows = session.query(Listing).filter(Listing.is_listed == True).all()
        return [to_dict(row) for row in rows]

def get_listing_by_mint(mint_address: str) -> dict | None:
    """Fetches all details for a single listing by its mint address."""
    with get_session() as session:
        row = session.query(Listing).filter(Listing.token_mint == mint_address).first()
        return to_dict(row)

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
        return [to_dict(row) for row in rows]

def create_user(wallet_address: str, tier: str = 'NORMAL') -> dict:
    """
    Creates a new user if they don't exist. Returns the user dict.
    """
    with get_session() as session:
        user = session.query(User).filter(User.wallet_address == wallet_address).first()
        if not user:
            user = User(wallet_address=wallet_address, tier=tier)
            session.add(user)
            # Create default settings for the user
            settings = UserSettings(user_wallet=wallet_address)
            session.add(settings)
            session.commit()
            logger.info(f"Created new user: {wallet_address} ({tier})")
        return to_dict(user)

def get_user(wallet_address: str) -> dict | None:
    """
    Fetches a user by wallet address.
    """
    with get_session() as session:
        user = session.query(User).filter(User.wallet_address == wallet_address).first()
        return to_dict(user)

def get_user_settings(wallet_address: str) -> dict | None:
    """
    Fetches settings for a specific user.
    """
    with get_session() as session:
        settings = session.query(UserSettings).filter(UserSettings.user_wallet == wallet_address).first()
        return settings.__dict__ if settings else None

def update_user_settings(wallet_address: str, settings_update: dict):
    """
    Updates the settings for a user.
    """
    with get_session() as session:
        session.query(UserSettings).filter(UserSettings.user_wallet == wallet_address).update(settings_update)
        session.commit()
