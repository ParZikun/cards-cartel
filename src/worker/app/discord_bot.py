import os
import discord
import logging
import asyncio
from typing import cast, Callable, Awaitable, Coroutine, Any
from discord import app_commands, ui, SelectOption
from discord.ext import commands

# Project imports
from .core.discord_embeds import create_snipe_embed, create_card_check_embed
from .core.magic_eden import check_listing_status_async
from .core.alt_data import get_alt_data_async
from database import main as database
from .core import utils

logger = logging.getLogger(__name__)

# --- Configuration ---
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")

CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
ROLE_ID = int(os.getenv("DISCORD_ROLE_ID", 0))

if not BOT_TOKEN or not CHANNEL_ID or not ROLE_ID:
    raise ValueError("DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, and DISCORD_ROLE_ID must be set in the .env file.")

# --- Helper function to reconstruct embed data ---
async def _reconstruct_embed_data(deal_data: dict):
    """
    Takes a flat dictionary from the database and reconstructs the
    listing_data and snipe_details dictionaries needed for the embed.
    """
    listing_data = {
        'listing_id': deal_data['listing_id'],
        'name': deal_data['name'],
        'grade_num': deal_data['grade_num'],
        'grade': deal_data['grade'],
        'category': deal_data['category'],
        'insured_value': deal_data['insured_value'],
        'grading_company': deal_data['grading_company'],
        'img_url': deal_data['img_url'],
        'grading_id': deal_data['grading_id'],
        'token_mint': deal_data['token_mint'],
        'price_amount': deal_data['price_amount'],
        'price_currency': deal_data['price_currency'],
        'listed_at': deal_data['listed_at'],
    }

    prices = await utils.get_price_in_both_currencies(deal_data['price_amount'], deal_data['price_currency']) # This function is async now
    listing_price_usd = prices['price_usdc'] if prices else 0
    alt_value = deal_data.get('alt_value', 0)
    
    difference_str = "N/A"
    if alt_value > 0 and listing_price_usd > 0:
        diff_percent = ((listing_price_usd - alt_value) / alt_value) * 100
        if diff_percent <= -30:
            difference_str = f"🟢 {diff_percent:+.2f}%"
        else:
            difference_str = f"{diff_percent:+.2f}%"

    snipe_details = {
        'alt_asset_id': deal_data['alt_asset_id'],
        'alt_value': alt_value,
        'avg_price': deal_data['avg_price'],
        'supply': deal_data['supply'],
        'lower_bound': deal_data['alt_value_lower_bound'],
        'upper_bound': deal_data['alt_value_upper_bound'],
        'confidence': deal_data['alt_value_confidence'],
        'listing_price_usd': listing_price_usd,
        'difference_str': difference_str,
    }
    
    return listing_data, snipe_details

# --- Interactive UI Components ---

class DealSelect(ui.Select):
    def __init__(self, deals: list[dict]):
        options = [
            SelectOption(label=deal['name'][:100], value=deal['listing_id'])
            for deal in deals
        ]
        super().__init__(placeholder="Select a deal to view details...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        listing_id = self.values[0]
        deal_data = await asyncio.to_thread(database.get_listing_by_id, listing_id)
        
        if not deal_data:
            await interaction.followup.send("Sorry, I couldn't find the details for that deal.", ephemeral=True)
            return
            
        listing_data, snipe_details = await _reconstruct_embed_data(deal_data)
        alert_level = deal_data.get('cartel_category', 'INFO')
        embed = create_snipe_embed(listing_data, snipe_details, alert_level, duration=0.0)
        await interaction.followup.send(embed=embed, ephemeral=True)

class DealSelectorView(ui.View):
    def __init__(self, deals: list[dict]):
        super().__init__(timeout=300)
        self.add_item(DealSelect(deals))

# --- Bot Subclass for Background Task ---

class CartelBot(commands.Bot):
    def __init__(self, snipe_queue: asyncio.Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.snipe_queue = snipe_queue

    async def setup_hook(self):
        # This is the proper way to start a background task.
        self.loop.create_task(self.snipe_consumer_loop())
        # Only sync when commands change to avoid rate limits.
        logging.info("Syncing Discord application commands...")
        await self.tree.sync() 
        logging.info("Discord bot setup hook complete. Consumer loop started.")

    async def on_ready(self):
        logging.info(f"✅ Discord bot logged in as {self.user}")
    async def snipe_consumer_loop(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        # Ensure we have a messageable channel (some channel types like CategoryChannel/ForumChannel are not messageable)
        if not channel or not hasattr(channel, "send"):
            logging.critical("❌ FATAL ERROR: Snipe consumer could not find a messageable channel with ID %s.", CHANNEL_ID)
            return
        channel_name = getattr(channel, "name", str(CHANNEL_ID))
        logging.info(f"Snipe consumer ready to post in #{channel_name}.")

        while True:
            try:
                snipe_data = await self.snipe_queue.get()
                
                listing_data = snipe_data.get('listing_data')
                snipe_details = snipe_data.get('snipe_details')
                alert_level = snipe_data.get('alert_level')
                duration = snipe_data.get('duration', 0.0)

                embed = create_snipe_embed(listing_data, snipe_details, alert_level, duration)
                ping_message = f"<@&{ROLE_ID}>" if alert_level.upper() != 'INFO' else ""
                
                # Cast to Messageable to satisfy static type-checkers after the runtime check above
                messageable = cast(discord.abc.Messageable, channel)
                await messageable.send(content=ping_message, embed=embed)
                logging.info(f"-> Sent {alert_level} alert to Discord for: {listing_data['name']}")

            except discord.errors.Forbidden as e:
                logging.error(f"PERMISSION ERROR: The bot cannot send messages in channel {CHANNEL_ID}. Check bot permissions. Error: {e}")
            except discord.errors.HTTPException as e:
                logging.error(f"NETWORK ERROR: Failed to send message to Discord. Error: {e}")
            except Exception as e: # Catch any other unexpected errors
                logging.exception("An unexpected error occurred in the Discord consumer loop.")
            finally:
                self.snipe_queue.task_done()

# --- Main entry point for the bot ---

async def start_discord_bot(queue: asyncio.Queue, recheck_skipped_callback: Callable[[str, discord.Interaction], Coroutine[Any, Any, None]]):
    intents = discord.Intents.default()
    intents.message_content = True # If you plan commands or need message content
    intents.members = True         # Required for Server Members Intent
    intents.presences = True       # Required for Presence Intent
    
    bot = CartelBot(snipe_queue=queue, command_prefix="!", intents=intents)
    
    @bot.tree.command(name="cartel_deals", description="Lists active deals from the database.")
    @app_commands.describe(category="Which category of deals to show")
    @app_commands.choices(category=[
        app_commands.Choice(name="Gold (Best)", value="GOLD"),
        app_commands.Choice(name="Red (Good)", value="RED"),
        app_commands.Choice(name="Blue (OK)", value="BLUE"),
        app_commands.Choice(name="All", value="ALL"),
    ])
    async def cartel_deals(interaction: discord.Interaction, category: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        category_map = {
            "GOLD": ["AUTOBUY"],
            "RED": ["GOOD"],
            "BLUE": ["OK"],
            "ALL": ["AUTOBUY", "GOOD", "OK"]
        }
        db_categories = category_map.get(category.value, [])
        
        deals = await asyncio.to_thread(database.get_active_deals_by_category, db_categories)
        
        if not deals:
            await interaction.followup.send(f"No active deals found for the **{category.name}** category.", ephemeral=True)
            return
            
        view = DealSelectorView(deals)
        await interaction.followup.send(f"Found **{len(deals)}** active deals in the **{category.name}** category. Select one to view details.", view=view, ephemeral=True)

    @bot.tree.command(name="cartel_inspect", description="Checks the status of a card by its mint address.")
    @app_commands.describe(mint_address="The mint address of the card to check.")
    async def cartel_inspect(interaction: discord.Interaction, mint_address: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        card_data = await check_listing_status_async(mint_address)

        if not card_data or card_data == 'not_found' or isinstance(card_data, str):
            await interaction.followup.send(f"Sorry, I couldn't find a card with the mint address `{mint_address}`.", ephemeral=True)
            return

        attrs = card_data.get('attributes') or []
        if not isinstance(attrs, list):
            attrs = []

        attributes = {}
        for attr in attrs:
            if isinstance(attr, dict):
                trait = attr.get('trait_type')
                value = attr.get('value')
                if trait is not None:
                    attributes[trait] = value

        cert_id = attributes.get('Grading ID')
        grade_num = attributes.get('GradeNum')
        company = attributes.get('Grading Company')

        alt_data = None
        if cert_id and grade_num and company:
            alt_data = await get_alt_data_async(cert_id, grade_num, company)

        embed = create_card_check_embed(card_data, alt_data)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="cartel_recheck", description="Admin: Re-analyzes listings that were previously skipped.")
    @app_commands.checks.has_role(ROLE_ID)
    @app_commands.describe(timeframe="Re-check listings from this period that were marked 'SKIP'")
    @app_commands.choices(timeframe=[
        app_commands.Choice(name="Last 1 Hour", value="1H"),
        app_commands.Choice(name="Last 2 Hours", value="2H"),
        app_commands.Choice(name="Last 1 Day", value="1D"),
        app_commands.Choice(name="Last 1 Week", value="1W"),
        app_commands.Choice(name="Last 1 Month", value="1M"),
        app_commands.Choice(name="All Skipped", value="ALL"),
    ])
    async def cartel_recheck(interaction: discord.Interaction, timeframe: app_commands.Choice[str]):
        """Handles the /cartel_recheck command."""
        await interaction.response.send_message(
            f"✅ **Acknowledged!** Starting a re-check of 'SKIP' listings from the **{timeframe.name}**. "
            "This may take a moment. I will notify you when it is complete.",
            ephemeral=True,
        )
        # Run the callback in the background
        asyncio.create_task(recheck_skipped_callback(timeframe.value, interaction))

    @cartel_recheck.error
    async def cartel_recheck_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message("❌ You do not have the required role to use this command.", ephemeral=True)
        else:
            await interaction.followup.send(f"An unexpected error occurred: {error}", ephemeral=True)

    try:
        await bot.start(str(BOT_TOKEN))
    except discord.errors.LoginFailure:
        logger.critical("❌ LOGIN FAILED: The DISCORD_BOT_TOKEN in your .env file is invalid.")
