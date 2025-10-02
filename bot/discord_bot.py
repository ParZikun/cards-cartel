import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from discord_embeds import create_snipe_embed

# --- Configuration ---
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
ROLE_ID = os.getenv("DISCORD_ROLE_ID")

if not BOT_TOKEN or not CHANNEL_ID or not ROLE_ID:
    raise ValueError("DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, and DISCORD_ROLE_ID must be set in the .env file.")

async def start_discord_bot(queue: asyncio.Queue):
    """
    Initializes and runs the Discord bot. It listens for items on an
    asyncio.Queue and sends them to the specified Discord channel.
    """
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"✅ Discord bot logged in as {bot.user}")
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print(f"❌ FATAL ERROR: Could not find channel with ID {CHANNEL_ID}. Check your .env file.")
            await bot.close()
            return
        print(f"Bot is ready and listening for snipes to post in #{channel.name}.")

        # --- Main Consumer Loop ---
        while True:
            try:
                snipe_data = await queue.get()
                
                listing_data = snipe_data.get('listing_data')
                snipe_details = snipe_data.get('snipe_details')
                alert_level = snipe_data.get('alert_level')

                embed = create_snipe_embed(listing_data, snipe_details, alert_level)
                ping_message = f"<@&{ROLE_ID}>" if alert_level.upper() == 'HIGH' else ""
                
                await channel.send(content=ping_message, embed=embed)
                print(f"    -> Sent {alert_level} alert to Discord for: {listing_data['name']}")

            except discord.errors.Forbidden:
                print(f"    ❌ PERMISSION ERROR: The bot cannot send messages in channel {CHANNEL_ID}.")
            except Exception as e:
                print(f"    ❌ An error occurred in the Discord consumer loop: {e}")
            finally:
                # --- FIX: This ensures the task is marked done no matter what ---
                queue.task_done()
    try:
        await bot.start(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("❌ LOGIN FAILED: The DISCORD_BOT_TOKEN in your .env file is invalid.")

