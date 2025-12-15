import os
import argparse
import logging
from sqlalchemy import create_engine, text

# Get DB config
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost") 
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "cards_cartel_db")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_engine():
    return create_engine(DATABASE_URL)

def list_users():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT wallet_address, tier, status FROM users"))
        rows = result.fetchall()
        if not rows:
            logger.info("No users found in database.")
            return

        logger.info(f"{'Wallet Address':<45} | {'Tier':<10} | {'Status'}")
        logger.info("-" * 70)
        for row in rows:
            logger.info(f"{row[0]:<45} | {row[1]:<10} | {row[2]}")

def add_user(wallet, tier="NORMAL"):
    engine = get_engine()
    with engine.connect() as conn:
        check = conn.execute(text("SELECT wallet_address FROM users WHERE wallet_address = :w"), {"w": wallet}).fetchone()
        if check:
            logger.info(f"User {wallet} already exists. Updating tier to {tier}...")
            conn.execute(text("UPDATE users SET tier = :t, status = 'ACTIVE' WHERE wallet_address = :w"), {"t": tier, "w": wallet})
            # Ensure Settings exist (in case they were deleted or missed)
            conn.execute(text("INSERT INTO user_settings (user_wallet) VALUES (:w) ON CONFLICT DO NOTHING"), {"w": wallet})
        else:
            logger.info(f"Adding new user {wallet} as {tier}...")
            # Create User
            conn.execute(text("INSERT INTO users (wallet_address, tier, status, created_at) VALUES (:w, :t, 'ACTIVE', NOW())"), {"w": wallet, "t": tier})
            # Create Settings (required for app to work)
            conn.execute(text("INSERT INTO user_settings (user_wallet) VALUES (:w) ON CONFLICT DO NOTHING"), {"w": wallet})
        
        conn.commit()
        logger.info("Success.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Cards Cartel Users")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List all users")
    
    add_parser = subparsers.add_parser("add", help="Add or update a user")
    add_parser.add_argument("wallet", help="Solana Wallet Address")
    add_parser.add_argument("--tier", default="NORMAL", choices=["NORMAL", "GOLD", "BLOCKED"], help="User Tier")

    args = parser.parse_args()

    if args.command == "list":
        list_users()
    elif args.command == "add":
        add_user(args.wallet, args.tier)
    else:
        parser.print_help()
