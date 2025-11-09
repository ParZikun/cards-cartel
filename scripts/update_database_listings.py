import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
import discord
from dotenv import load_dotenv

# Add the project root to the Python path to allow imports from 'src'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.database import main as database
from src.worker.app.core import magic_eden as me
from src.worker.app.core import alt_data as alt
from src.worker.app.core import utils
from src.worker.app.discord_bot import CartelBot # Use the existing bot

# --- Environment Variable Loading ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# --- Discord Configuration ---
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


async def analyze_and_update_listing(listing: dict, queue: asyncio.Queue):
    """
    Analyzes a single listing, updates it in the database, and sends notifications if it's a deal.
    """
    listing_id = listing.get('listing_id')
    token_mint = listing.get('token_mint')
    name = listing.get('name')
    
    logger.info(f"--- Analyzing: {name} ({listing_id}) ---")

    if not listing_id:
        logger.warning(f"Listing {name} with mint {token_mint} has no listing_id. Skipping.")
        return

    try:
        # 1. Get ALT data
        alt_data = await alt.get_alt_data_async(
            listing['grading_id'],
            listing.get('grade_num', 0),
            listing['grading_company']
        )

        if not alt_data:
            logger.warning(f"Could not fetch ALT data for {name}. Marking as SKIP.")
            await asyncio.to_thread(database.skip_listing, listing_id, 'SKIP')
            return

        # 2. Get current prices
        current_price_sol = listing.get('price_amount')
        if not current_price_sol:
            logger.warning(f"Could not get current price for {name}. Skipping update.")
            return
            
        prices = await utils.get_price_in_both_currencies(current_price_sol, 'SOL')
        if not prices:
            logger.error(f"Could not convert price for {name}. Skipping.")
            return

        # 3. Categorize the deal
        listing_price_usd = prices.get('price_usdc', 0)
        snipe_details = {**alt_data, 'listing_price_usd': listing_price_usd}
        
        cartel_category = 'SKIP'
        alert_level = 'INFO'
        alt_value = snipe_details.get('alt_value', 0)
        alt_confidence = snipe_details.get('confidence', 0)
        difference_str = "N/A"

        if alt_value > 0 and listing_price_usd > 0 and alt_confidence > 60:
            diff_percent = ((listing_price_usd - alt_value) / alt_value) * 100
            if diff_percent <= -30:
                cartel_category = 'AUTOBUY'
                alert_level = 'GOLD'
                difference_str = f"🟢 {diff_percent:+.2f}%"
            elif diff_percent <= -20:
                cartel_category = 'GOOD'
                alert_level = 'HIGH'
                difference_str = f"{diff_percent:+.2f}%"
            elif diff_percent <= -15:
                cartel_category = 'OK'
                difference_str = f"{diff_percent:+.2f}%"
            else:
                difference_str = f"{diff_percent:+.2f}%"
        
        snipe_details['difference_str'] = difference_str

        # 4. Update the database
        update_payload = {
            "price_amount": current_price_sol,
            "alt_asset_id": snipe_details.get('alt_asset_id'),
            "alt_value": snipe_details.get('alt_value'),
            "avg_price": snipe_details.get('avg_price'),
            "supply": snipe_details.get('supply'),
            "alt_value_lower_bound": snipe_details.get('lower_bound'),
            "alt_value_upper_bound": snipe_details.get('upper_bound'),
            "alt_value_confidence": snipe_details.get('confidence'),
            "cartel_category": cartel_category,
            "last_analyzed_at": datetime.now(timezone.utc)
        }
        await asyncio.to_thread(database.update_listing_details, listing_id, update_payload)
        logger.info(f"Updated '{name}' with price: {current_price_sol} SOL and category: {cartel_category}")

        # 5. Send Discord notification if it's a good deal
        if cartel_category in ['AUTOBUY', 'GOOD']:
            full_listing_data = await asyncio.to_thread(database.get_listing_by_id, listing_id)
            if full_listing_data:
                notification_data = {
                    'listing_data': full_listing_data,
                    'snipe_details': snipe_details,
                    'alert_level': alert_level,
                    'duration': 0.0 # Duration is calculated in the worker, can be 0 here
                }
                await queue.put(notification_data)
                logger.info(f"Queued '{cartel_category}' deal notification for: {full_listing_data['name']}")


    except Exception as e:
        logger.exception(f"An unexpected error occurred while processing listing {listing_id}. Marking as ERROR.")
        if listing_id:
            await asyncio.to_thread(database.skip_listing, listing_id, 'ERROR')
    finally:
        await asyncio.sleep(1) # Be respectful to APIs

async def sync_with_magic_eden(queue: asyncio.Queue):
    """
    Main function to sync the database with Magic Eden, check for deals, and update listings.
    """
    logger.info("--- Starting full sync with Magic Eden ---")

    # 1. Fetch all listings from Magic Eden
    me_listings = await me.fetch_all_listings_paginated_async()
    me_listings_map = {listing['token_mint']: listing for listing in me_listings}
    logger.info(f"Fetched {len(me_listings_map)} unique listings from Magic Eden.")

    # 2. Fetch all active listings from the database
    db_listings = await asyncio.to_thread(database.get_all_active_listings)
    db_listings_map = {listing['token_mint']: listing for listing in db_listings}
    logger.info(f"Found {len(db_listings_map)} active listings in the database.")

    # 3. Identify delisted items
    delisted_mints = set(db_listings_map.keys()) - set(me_listings_map.keys())
    logger.info(f"Found {len(delisted_mints)} listings to mark as delisted.")
    for mint in delisted_mints:
        await asyncio.to_thread(database.update_listing_status, mint, is_listed=False)

    # 4. Process new and existing listings
    for i, (mint, me_listing) in enumerate(me_listings_map.items()):
        logger.info(f"--- ({i+1}/{len(me_listings_map)}) Processing mint: {mint} ---")
        db_listing = db_listings_map.get(mint)

        if not db_listing:
            # New listing
            logger.info(f"New listing found: {me_listing['name']}. Saving to database.")
            await asyncio.to_thread(database.save_listing, [me_listing])
            # The listing is now in the DB, so we can analyze it.
            # We need the full listing data from the DB, especially the listing_id.
            new_db_listing = await asyncio.to_thread(database.get_listing_by_mint, mint)
            if new_db_listing:
                await analyze_and_update_listing(new_db_listing, queue)
            else:
                logger.error(f"Could not retrieve new listing {mint} from DB after saving.")
        else:
            # Existing listing, re-analyze
            logger.info(f"Existing listing found: {me_listing['name']}. Re-analyzing.")
            # We pass the existing DB listing, but we need to update the price from ME
            db_listing['price_amount'] = me_listing['price_amount']
            await analyze_and_update_listing(db_listing, queue)

    logger.info("--- Full database sync and re-check process complete! ---")


async def main():
    """
    Sets up the Discord bot and runs the sync process.
    """
    logger.info("Initializing Discord bot and sync process...")

    if not BOT_TOKEN:
        logger.critical("DISCORD_BOT_TOKEN environment variable not set. Cannot start bot.")
        return

    queue = asyncio.Queue()
    
    # We don't need commands for this script, so a minimal bot is fine.
    intents = discord.Intents.default()
    bot = CartelBot(snipe_queue=queue, command_prefix="!", intents=intents)

    async def runner():
        await bot.wait_until_ready()
        await sync_with_magic_eden(queue)
        logger.info("Sync finished. Waiting for Discord queue to empty...")
        await queue.join() # Wait for all notifications to be sent
        logger.info("Discord queue empty. Shutting down bot.")
        await bot.close()

    # Run the bot and the sync process concurrently
    try:
        await asyncio.gather(
            bot.start(BOT_TOKEN),
            runner()
        )
    except discord.errors.LoginFailure:
        logger.critical("LOGIN FAILED: The DISCORD_BOT_TOKEN is invalid.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()
        logger.info("Script finished.")


if __name__ == "__main__":
    asyncio.run(main())
