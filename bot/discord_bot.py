import os
import discord
import asyncio
from discord import app_commands, ui, SelectOption
from discord.ext import commands

# Project imports
from discord_embeds import create_snipe_embed
import database
import utils

# --- Configuration ---
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
ROLE_ID = os.getenv("DISCORD_ROLE_ID")

if not BOT_TOKEN or not CHANNEL_ID or not ROLE_ID:
    raise ValueError("DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, and DISCORD_ROLE_ID must be set in the .env file.")

# --- Helper function to reconstruct embed data ---
def _reconstruct_embed_data(deal_data: dict):
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

    prices = utils.get_price_in_both_currencies(deal_data['price_amount'], deal_data['price_currency'])
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
            
        listing_data, snipe_details = _reconstruct_embed_data(deal_data)
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
        await self.tree.sync()
        print("✅ Slash commands synced.")

    async def on_ready(self):
        print(f"✅ Discord bot logged in as {self.user}")

    async def snipe_consumer_loop(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            print("❌ FATAL ERROR: Snipe consumer could not find channel.")
            return
        print(f"Snipe consumer ready to post in #{channel.name}.")

        while True:
            try:
                snipe_data = await self.snipe_queue.get()
                
                listing_data = snipe_data.get('listing_data')
                snipe_details = snipe_data.get('snipe_details')
                alert_level = snipe_data.get('alert_level')
                duration = snipe_data.get('duration', 0.0)

                embed = create_snipe_embed(listing_data, snipe_details, alert_level, duration)
                ping_message = f"<@&{ROLE_ID}>" if alert_level.upper() != 'INFO' else ""
                
                await channel.send(content=ping_message, embed=embed)
                print(f"    -> Sent {alert_level} alert to Discord for: {listing_data['name']}")

            except discord.errors.Forbidden:
                print(f"    ❌ PERMISSION ERROR: The bot cannot send messages in channel {CHANNEL_ID}.")
            except Exception as e:
                print(f"    ❌ An error occurred in the Discord consumer loop: {e}")
            finally:
                self.snipe_queue.task_done()

# --- Main entry point for the bot ---

async def start_discord_bot(queue: asyncio.Queue):
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

    try:
        await bot.start(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("❌ LOGIN FAILED: The DISCORD_BOT_TOKEN in your .env file is invalid.")
