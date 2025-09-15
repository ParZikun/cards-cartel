import time
import asyncio
import database
import get_magic_eden_data as me
import get_alt_data as alt
import utils
import discord_bot

async def enrich_unprocessed_listings(queue: asyncio.Queue):
    """
    Slowly enriches all listings in the database that are missing ALT data.
    Runs once at startup before the watchdog.
    """
    unprocessed_listings = await asyncio.to_thread(database.get_listings_without_alt_data)
    if not unprocessed_listings:
        print("✅ All existing listings are already enriched.")
        return

    print(f"\n--- Found {len(unprocessed_listings)} unprocessed listings. Starting enrichment process (this will be slow)... ---")
    
    # Process them one by one with a delay to be respectful to the ALT API
    for i, listing in enumerate(unprocessed_listings):
        await enrich_and_send(listing, queue)
        # We add the sleep here to ensure a gap between each listing's API calls
        await asyncio.sleep(3) # Respectful 3-second delay

async def enrich_and_send(listing: dict, queue: asyncio.Queue):
    """Single-listing processing pipeline: Get ALT data -> Save -> Queue for Discord."""
    start_time = time.time()
    print(f"  -> Processing: {listing.get('name')} ({listing.get('grading_id')})")
    
    try:
        # Run synchronous network calls in a separate thread to not block the event loop
        loop = asyncio.get_running_loop()
        processed_alt_data = await loop.run_in_executor(
            None, alt.get_alt_data, 
            listing['grading_id'], 
            str(listing.get('grade_num', 0)), 
            listing['grading_company']
        )
        
        if processed_alt_data:
            # BUSINESS CONDITION HERE WHICH WILL DECIDE THE alert_level and if we wanna process it or not 
            prices = utils.get_price_in_both_currencies(listing['price_amount'], listing['price_currency'])
            if prices:
                snipe_details = {**processed_alt_data, 'listing_price_usd': prices['price_usdc']}
            else:
                print("Error Converting Price to USDC")
                raise

            listing_price_usd = prices['price_usdc']
            alt_value = processed_alt_data.get('alt_value', 0)

            alert_level = None
            difference_str = "N/A"

            if alt_value > 0 and listing_price_usd > 0:
                difference_percent = ((listing_price_usd - alt_value) / alt_value) * 100
                
                # --- AUTOSNIPE (DISABLED FOR NOW) ---
                # Format the difference string for the embed
                if difference_percent <= -30:
                    print(f"  -> AUTOSNIPE TRIGGERED (LOGIC DISABLED)")
                    alert_level = 'HIGH'
                    difference_str = f"🟢 **{difference_percent:.2f}%**"

                elif difference_percent <= -20:
                    alert_level = 'HIGH'
                    difference_str = f"{difference_percent:+.2f}%"

                elif difference_percent <= -15:
                    alert_level = 'INFO'
                    difference_str = f"{difference_percent:+.2f}%"

                else:
                    difference_str = f"{difference_percent:+.2f}%"
            
                snipe_details['difference_str'] = difference_str # Add to details for the embed

            if alert_level:
                print(f"    -> Found a {alert_level} snipe! Queueing for Discord.")
                await queue.put({
                    'listing_data': listing,
                    'snipe_details': snipe_details,
                    'alert_level': alert_level
                })
                duration = time.time() - start_time
                await asyncio.to_thread(database.update_listing_alt_data, listing['listing_id'], processed_alt_data)
                print(f"    ✅ Success. Processing took {duration:.3f} seconds.")
            else:
                print(f"    -> Listing did not meet snipe criteria.")

            # await queue.put({
            #     'listing_data': listing,
            #     'snipe_details': snipe_details,
            #     'alert_level': 'HIGH' # Change this later when sniper logic is added
            # })     
        else:
            print(f"    ⚠️ Could not fetch ALT data for {listing.get('name')}.")

    except Exception as e:
        print(f"    ❌ An unexpected error occurred while processing {listing.get('name')}: {e}")

async def watchdog(queue: asyncio.Queue):
    """The main watchdog loop."""
    print("\n--- 🚀 Starting Watchdog ---")
    processed_ids = await asyncio.to_thread(database.get_all_listing_ids)
    print(f"Loaded {len(processed_ids)} previously processed listing IDs.")
    loop = asyncio.get_running_loop()

    while True:
        try:
            print(f"\n[Watchdog at {time.strftime('%H:%M:%S')}] Checking for new listings...")
            # Run the synchronous ME fetch in a separate thread
            new_listings = await loop.run_in_executor(None, me.fetch_new_listings, processed_ids)
            
            if new_listings:
                print(f"🔥 Found {len(new_listings)} new items!")
                # Save the base listing data first
                await asyncio.to_thread(database.save_listings, new_listings)
                
                # Create a task for each new listing to be processed concurrently
                tasks = []
                for listing in new_listings:
                    processed_ids.add(listing['listing_id'])
                    tasks.append(enrich_and_send(listing, queue))
                
                await asyncio.gather(*tasks) # Run all processing tasks in parallel
                
            else:
                print("✅ No new listings found.")
            await asyncio.sleep(0.6)
        except Exception as e:
            print(f"❌ An unexpected error in watchdog loop: {e}")
            await asyncio.sleep(10)

async def main():
    """The main entry point for the application."""
    snipe_queue = asyncio.Queue()

    print("---  sniper booting up ---")
    await asyncio.to_thread(database.init_db)
    
    if not await asyncio.to_thread(database.get_all_listing_ids):
        print("Database is empty. Populating with the latest 100 listings...")
        initial_listings, _ = await asyncio.to_thread(me.fetch_initial_listings, 100)
        if initial_listings:
            await asyncio.to_thread(database.save_listings, initial_listings)
            print(f"✅ Initial population complete. Saved {len(initial_listings)} listings.")

    # Start the Discord bot in the background and the watchdog in the foreground
    discord_task = asyncio.create_task(discord_bot.start_discord_bot(snipe_queue))

    # Enrich any listings that are missing data before starting the watchdog
    await enrich_unprocessed_listings(snipe_queue)

    watchdog_task = asyncio.create_task(watchdog(snipe_queue))

    await asyncio.gather(discord_task, watchdog_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down sniper.")




# import time
# import database
# import get_magic_eden_data as me
# import get_alt_data as alt

# def enrich_listings_with_alt_data(listings_to_process: list, slow_mode: bool = False):
#     """
#     Fetches ALT data for a list of listings and saves it to the database.
#     Can run in a slow, respectful mode for enriching old listings.
#     """
#     total_listings = len(listings_to_process)
#     for i, listing in enumerate(listings_to_process):
#         start_time = time.time()
        
#         prefix = f"Enriching old listing ({i+1}/{total_listings})" if slow_mode else "Processing new listing"
#         print(f"  -> {prefix}: {listing.get('name')} ({listing.get('grading_id')})")
        
#         try:
#             processed_alt_data = alt.get_alt_data(
#                 cert_id=listing['grading_id'],
#                 grade=listing['grade_num'],
#                 company=listing['grading_company']
#             )
            
#             if processed_alt_data:
#                 # Save the enriched data back to the database
#                 database.update_listing_alt_data(listing['listing_id'], processed_alt_data)
                
#                 # For new listings, print the processing time metric
#                 if not slow_mode:
#                     end_time = time.time()
#                     duration = end_time - start_time
#                     print(f"    ✅ Success. Processing took {duration:.3f} seconds.")
#             else:
#                 print(f"    ⚠️ Could not fetch ALT data for {listing.get('name')}.")

#         except Exception as e:
#             print(f"    ❌ An unexpected error occurred while processing {listing.get('name')}: {e}")

#         # If in slow mode for enriching old data, wait between requests
#         if slow_mode:
#             time.sleep(3) # Respectful delay to avoid flagging

# def watchdog():
#     """
#     The main infinite loop that checks for and processes new listings at high speed.
#     """
#     print("\n--- 🚀 Starting Watchdog ---")
    
#     # Load the IDs of all listings we have ever seen into memory
#     processed_ids = database.get_all_listing_ids()
#     print(f"Loaded {len(processed_ids)} previously processed listing IDs.")

#     while True:
#         try:
#             print(f"\n[Watchdog at {time.strftime('%H:%M:%S')}] Checking for new listings...")
#             new_listings = me.fetch_new_listings(processed_ids)
            
#             if new_listings:
#                 print(f"🔥 Found {len(new_listings)} new items!")
                
#                 # 1. Save all new listings to the DB first to mark them as seen
#                 database.save_listings(new_listings)
                
#                 # 2. Update our in-memory set of processed IDs
#                 for item in new_listings:
#                     processed_ids.add(item['listing_id'])
                
#                 # 3. Process each new listing to get ALT data immediately
#                 enrich_listings_with_alt_data(new_listings, slow_mode=False)
                
#             else:
#                 print("✅ No new listings found.")

#             # Wait before the next check
#             time.sleep(0.6) # High-frequency check for new snipes

#         except Exception as e:
#             print(f"❌ An unexpected error occurred in the watchdog loop: {e}")
#             print("Waiting for 10 seconds before retrying...")
#             time.sleep(10)

# if __name__ == "__main__":
#     # 1. Ensure the database and table exist
#     database.init_db()

#     # 2. Check if the DB is empty. If so, do a one-time full population from ME.
#     if not database.get_all_listing_ids():
#         print("Database is empty. Performing one-time initial population from Magic Eden...")
#         all_listings, _ = me.fetch_all_listings()
#         if all_listings:
#             database.save_listings(all_listings)
#             print(f"✅ Initial ME population complete. Saved {len(all_listings)} listings.")
    
#     # 3. Catch up on ALT data for any old listings that are missing it.
#     # This runs once at startup.
#     old_listings_to_enrich = database.get_listings_without_alt_data()
#     if old_listings_to_enrich:
#         print("\n--- Enriching Old Listings ---")
#         enrich_listings_with_alt_data(old_listings_to_enrich, slow_mode=True)
#         print("✅ Old listings enriched.")
#     else:
#         print("\n✅ All existing listings are already enriched.")
    
#     # 4. Start the continuous watchdog for new listings
#     watchdog()

