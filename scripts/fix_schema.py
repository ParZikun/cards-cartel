import os
import logging
from sqlalchemy import create_engine, text

# Reuse existing environment variables or defaults
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "cards_cartel")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_schema():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # Check if column exists first to be safe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user_settings' AND column_name='rpc_endpoint';
            """)
            result = connection.execute(check_query).fetchone()
            
            if not result:
                logger.info("Column 'rpc_endpoint' missing. Adding it now...")
                alter_query = text("ALTER TABLE user_settings ADD COLUMN rpc_endpoint VARCHAR DEFAULT 'https://api.mainnet-beta.solana.com';")
                connection.execute(alter_query)
                logger.info("Successfully added 'rpc_endpoint' to 'user_settings'.")
            else:
                logger.info("Column 'rpc_endpoint' already exists.")
                
    except Exception as e:
        logger.error(f"Error fixing schema: {e}")

if __name__ == "__main__":
    fix_schema()
