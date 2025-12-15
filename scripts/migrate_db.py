import os
import logging
from sqlalchemy import create_engine, text

# Get DB config from env or defaults (matching container defaults)
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost") 
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "cards_cartel_db")

# Construct URL
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """
    Checks for missing columns in user_settings and adds them.
    Useful for existing environments where create_all() won't update tables.
    """
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            logger.info(f"Connected to {DB_NAME} at {DB_HOST}")
            
            # 1. Check/Add rpc_endpoint
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user_settings' AND column_name='rpc_endpoint';
            """)
            result = connection.execute(check_query).fetchone()
            
            if not result:
                logger.info("Column 'rpc_endpoint' missing. Adding it now...")
                alter_query = text("ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS rpc_endpoint VARCHAR DEFAULT 'https://api.mainnet-beta.solana.com';")
                connection.execute(alter_query)
                connection.commit()
                logger.info("Successfully added 'rpc_endpoint'.")
            else:
                logger.info("Column 'rpc_endpoint' already exists.")

            # 2. Check/Add jito_tip_amount 
            check_query_jito = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user_settings' AND column_name='jito_tip_amount';
            """)
            result_jito = connection.execute(check_query_jito).fetchone()
            
            if not result_jito:
                 logger.info("Column 'jito_tip_amount' missing. Adding it now...")
                 alter_query = text("ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS jito_tip_amount FLOAT DEFAULT 0.001;")
                 connection.execute(alter_query)
                 connection.commit()
                 logger.info("Successfully added 'jito_tip_amount'.")

            # 3. Check/Add encrypted_private_key
            check_query_key = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user_settings' AND column_name='encrypted_private_key';
            """)
            result_key = connection.execute(check_query_key).fetchone()
            
            if not result_key:
                 logger.info("Column 'encrypted_private_key' missing. Adding it now...")
                 alter_query = text("ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS encrypted_private_key VARCHAR DEFAULT NULL;")
                 connection.execute(alter_query)
                 connection.commit()
                 logger.info("Successfully added 'encrypted_private_key'.")

    except Exception as e:
        logger.error(f"Migration Failed: {e}")

if __name__ == "__main__":
    migrate()
