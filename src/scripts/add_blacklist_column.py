import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add parent directory to path to import database config if needed, 
# but here we can just use the same env vars.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "cards_cartel")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run_migration():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='user_settings' AND column_name='blacklisted_keywords'"))
            if result.fetchone():
                logger.info("Column 'blacklisted_keywords' already exists.")
            else:
                logger.info("Adding 'blacklisted_keywords' column...")
                conn.execute(text("ALTER TABLE user_settings ADD COLUMN blacklisted_keywords TEXT DEFAULT 'black star,sticker,stickers'"))
                conn.commit()
                logger.info("Migration successful!")
        except Exception as e:
            logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
