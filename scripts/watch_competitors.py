import asyncio
import os
import sys
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord import Webhook
import aiohttp

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("COMPETITOR_WATCH")

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from worker.app.core import magic_eden

# Load Env
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(project_root, '.env.local')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Configuration
# Replace with actual competitor wallets or load from ENV
COMPETITORS = [
    # "Ghasty" from user screenshot
    "Ghasty23s5VnRBFv83VxewvtL44ZBRdsEbsE4GRZBzmJ", 
    "CcLtd9vWESP7mXKxfzQPgdhJ3hMxztaiJYsWKK9hrVMM"
]

# State
SEEN_SIGNATURES = set()
WEBHOOK_URL = os.getenv("COMPETITOR_WEBHOOK_URL") # User needs to set this, or reusing specific channel?

# If no webhook, maybe use bot token? Webhook is simpler for a script.
# Fallback: Print to console if no webhook.

async def send_discord_alert(activity, wallet):
    if not WEBHOOK_URL:
        logger.warning("No COMPETITOR_WEBHOOK_URL set. Skipping Discord alert.")
        return

    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(WEBHOOK_URL, session=session)
        
        # Parse Activity
        act_type = activity.get('type', 'Unknown').upper()
        price = activity.get('price', 0)
        token_mint = activity.get('tokenMint', 'N/A')
        image = activity.get('image', '')
        name = activity.get('name') or f"Item {token_mint[:8]}"
        signature = activity.get('signature', 'N/A')
        
        # Color based on type
        if 'BUY' in act_type:
            color = 0x00ff00 # Green
            emoji = "💸"
        elif 'LIST' in act_type:
            color = 0xff9900 # Orange
            emoji = "🏷️"
        else:
            color = 0x808080
            emoji = "ℹ️"

        embed = discord.Embed(
            title=f"{emoji} Competitor Activity: {act_type}",
            description=f"**Wallet**: `{wallet[:6]}...{wallet[-4:]}`\n**Action**: {act_type}\n**Item**: {name}\n**Price**: {price} SOL",
            color=color,
            timestamp=datetime.utcnow()
        )
        if image:
            embed.set_thumbnail(url=image)
        
        embed.add_field(name="Mint", value=f"`{token_mint}`", inline=False)
        embed.add_field(name="Links", value=f"[Solscan](https://solscan.io/tx/{signature}) • [Magic Eden](https://magiceden.io/item-details/{token_mint})", inline=False)
        embed.set_footer(text=f"Competitor Watch • {wallet}")

        await webhook.send(embed=embed, username="Spy Bot")

async def monitor_loop():
    logger.info(f"👀 Starting Monitor for {len(COMPETITORS)} wallets...")
    
    # Initialize seen signatures to avoid spamming old stuff on restart
    # Fetch once and mark as seen without alerting
    for wallet in COMPETITORS:
        activities = await magic_eden.get_wallet_activities_async(wallet, limit=20)
        if activities:
            for act in activities:
                sig = act.get('signature')
                if sig: SEEN_SIGNATURES.add(sig)
    
    logger.info(f"✅ Initialized. Ignoring {len(SEEN_SIGNATURES)} historical events.")
    
    while True:
        try:
            for wallet in COMPETITORS:
                activities = await magic_eden.get_wallet_activities_async(wallet, limit=5)
                
                if not activities:
                    continue
                    
                for act in activities:
                    sig = act.get('signature')
                    if not sig: continue
                    
                    if sig not in SEEN_SIGNATURES:
                        # NEW EVENT
                        SEEN_SIGNATURES.add(sig)
                        
                        # Filter for interesting events? (Buy/Sell/List)
                        act_type = act.get('type')
                        if act_type in ['buyNow', 'list', 'delist', 'cancelList']: 
                           logger.info(f"🔔 New Activity [Wallet: {wallet[:6]}]: {act_type}")
                           await send_discord_alert(act, wallet)
                        else:
                            logger.debug(f"Ignored activity type: {act_type}")
            
            await asyncio.sleep(60) # Chill poll
            
        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        pass
