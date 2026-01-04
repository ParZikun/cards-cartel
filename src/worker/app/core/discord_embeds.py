import discord
from datetime import datetime

# --- IMPORTANT: Replace these with your actual custom emoji IDs ---
# To get an emoji ID, type \:emoji_name: in Discord and it will show you the ID.
SOL_EMOTE = "<:sol:1381357455279128747>" 
USDC_EMOTE = '<:usdc:1417030766663041174>'
CC_EMOTE = "<:CC:1416955345359732841>"
ME_EMOTE = "<:ME:1416955336258097213>"
ALT_EMOTE = "<:ALT:1416955327303389335>"
DOLLAR_EMOTE = "<:dollar:1417032571371655309>"

def create_snipe_embed(listing_data: dict, snipe_details: dict, alert_level: str, duration: float = 0.0, reason: str = None):
    """
    Creates a rich discord.Embed object based on the new design.
    """
    footer_icon = "https://emoji.discadia.com/emojis/7b975e64-50d6-4710-a49f-e55bc1e629e2.png"
    alert_upper = alert_level.upper()
    
    # --- Color & Title Logic ---
    if alert_upper == 'AUTOBUY':
        color = 0x00ff00  # Green
        footer_text = "💰 AUTOBUY EXECUTED"
    elif alert_upper == 'GOLD':
        color = 0xffd700  # Gold
        footer_text = "🏆 GOLD TIER SNIPE"
    elif alert_upper == 'HIGH':
        color = 0xff0000  # Red
        footer_text = "🚨 HIGH ALERT SNIPE"
    elif alert_upper in ['SUSPICIOUS', 'RISK', 'UNDETERMINED']:
        color = 0xffa500 # Orange
        footer_text = "⚠️ RISK / WARNING"
    else:
        color = 0x0099ff # Blue
        footer_text = "ℹ️ INFO ALERT"

    # Append duration to the footer text
    if duration > 0:
        footer_text += f" | ⏱️ {duration:.2f}s"
    
    # Add Mint to Footer for Searchability assurance
    footer_text += f" | {listing_data.get('token_mint')}"

    me_link = f"https://magiceden.io/item-details/{listing_data.get('token_mint')}"
    cc_link = f"https://collectorcrypt.com/assets/solana/{listing_data.get('token_mint')}"
    alt_link = f"https://app.alt.xyz/research/{snipe_details.get('alt_asset_id')}" if snipe_details.get('alt_asset_id') else "https://app.alt.xyz/"

    # --- Construct the Multi-line Description ---
    # Searchable Keywords in description
    description = (
        f"📍 Mint: ```{listing_data.get('token_mint')}```"
        f"🏢 Grading Company: **`{listing_data.get('grading_company')}`**\n"
        f"🆔 Grading ID: **`{listing_data.get('grading_id')}`**\n"
        f"🈴 Grade: **`{listing_data.get('grade')}`**\n"
        f"{DOLLAR_EMOTE} Insured Value: {USDC_EMOTE} **`{listing_data.get('insured_value'):.2f}`**\n"        
        f"#️⃣ Supply: **`{snipe_details.get('supply', 'N/A')}`**\n\n"
    )
    
    # Add Reason if provided (e.g. for Risk/Suspicious)
    if reason:
        description += f"⚠️ **REASON:** {reason}\n\n"

    description += (
        f"{ALT_EMOTE} [ALT.XYZ]({alt_link})\n"
        f"{ME_EMOTE} [Magic Eden]({me_link})\n"
        f"{CC_EMOTE} [Collector Crypt]({cc_link})\n"
    )
    
    # Enhanced Title with Category
    title_prefix = f"[{listing_data.get('grading_company', 'Card')} {listing_data.get('grade', '')}]"
    embed_title = f"{title_prefix} {listing_data.get('name', 'Unknown')}"

    # --- Create the Embed ---
    embed = discord.Embed(
        title=embed_title,
        url=me_link,
        description=description,
        color=color,
    )

    # --- Add Inline Fields for Stats ---
    currency_emote = SOL_EMOTE if listing_data.get('price_currency') == 'SOL' else USDC_EMOTE
    
    # 1. Listed Price
    embed.add_field(
        name=f"🏷️ Listed Price", 
        value=f"{currency_emote} **{listing_data.get(f'price_amount', 0):.2f}**\n*({USDC_EMOTE} {snipe_details.get('listing_price_usd', 0):.0f})*", 
        inline=True
    )
    
    # 2. Alt Value
    embed.add_field(
        name=f"📊 Alt Value", 
        value=f"{USDC_EMOTE} **{snipe_details.get('alt_value', 0):.0f}**", 
        inline=True
    )
    
    # 3. Discount (Difference)
    embed.add_field(name="📉 Discount", value=snipe_details.get('difference_str', 'N/A'), inline=True)
    
    # 4. Cartel Avg
    embed.add_field(name=f"📈 Cartel Avg", value=f"{USDC_EMOTE} {snipe_details.get('avg_price', 0):.0f}", inline=True)
    
    # 5. Confidence
    embed.add_field(name="🎯 Confidence", value=f"{snipe_details.get('confidence', 0)}%", inline=True)

    # 6. Range
    embed.add_field(name="↔️ Range", value=f"{USDC_EMOTE} {snipe_details.get('lower_bound', 0):.0f} - {snipe_details.get('upper_bound', 0):.0f}", inline=True)

    if listing_data.get('img_url'):
        embed.set_image(url=listing_data.get('img_url'))
    
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    
    return embed

def create_card_check_embed(card_data: dict, alt_data: dict | None):
    """
    Creates a rich discord.Embed for checking a single card's status.
    """
    # --- Basic Card Info ---
    list_status = card_data.get('listStatus', 'unlisted')
    color = 0x00ff00 if list_status == 'listed' else 0xff0000  # Green for listed, Red for unlisted
    footer_text = f"Status: {list_status.upper()}"
    
    mint_address = card_data.get('mintAddress')
    me_link = f"https://magiceden.io/item-details/{mint_address}"
    cc_link = f"https://collectorcrypt.com/assets/solana/{mint_address}"

    # --- Attributes ---
    attributes = {attr['trait_type']: attr['value'] for attr in card_data.get('attributes', [])}
    grading_company = attributes.get('Grading Company', 'N/A')
    grading_id = attributes.get('Grading ID', 'N/A')
    grade = attributes.get('The Grade', 'N/A')
    insured_value = float(attributes.get('Insured Value', 0))

    # --- Description ---
    description = (
        f"📍 Mint: ```{mint_address}```"
        f"🏢 Grading Company: **`{grading_company}`**\n"
        f"🆔 Grading ID: **`{grading_id}`**\n"
        f"🈴 Grade: **`{grade}`**\n"
        f"{DOLLAR_EMOTE} Insured Value: {USDC_EMOTE} **`{insured_value:.2f}`**\n"
    )

    if alt_data and alt_data.get('supply'):
        description += f"#️⃣ Supply: **`{alt_data.get('supply', 'N/A')}`**\n\n"
    
    alt_link = "https://app.alt.xyz/"
    if alt_data and alt_data.get('alt_asset_id'):
        alt_link = f"https://app.alt.xyz/research/{alt_data['alt_asset_id']}"

    description += (
        f"{ALT_EMOTE} [ALT.XYZ]({alt_link})\n"
        f"{ME_EMOTE} [Magic Eden]({me_link})\n"
        f"{CC_EMOTE} [Collector Crypt]({cc_link})\n"
    )

    # --- Create Embed ---
    embed = discord.Embed(
        title=card_data.get('name', "Unknown Card"),
        url=me_link,
        description=description,
        color=color,
    )

    # --- Price Fields (if listed) ---
    if list_status == 'listed':
        price = card_data.get('price', 0)
        embed.add_field(name=f"{ME_EMOTE} Listed Price", value=f"{SOL_EMOTE} {price:.4f}", inline=True)

    # --- ALT Data Fields (if available) ---
    if alt_data:
        embed.add_field(name="Alt Value", value=f"{USDC_EMOTE} {alt_data.get('alt_value', 0):.2f}", inline=True)
        embed.add_field(name="Cartel AVG", value=f"{USDC_EMOTE} {alt_data.get('avg_price', 0):.2f}", inline=True)
        embed.add_field(name="ALT Confidence", value=f"{alt_data.get('confidence', 0)}%", inline=True)
        embed.add_field(name="ALT Value Range", value=f"{USDC_EMOTE} {alt_data.get('lower_bound', 0):.2f} - {alt_data.get('upper_bound', 0):.2f}", inline=True)

    if card_data.get('image'):
        embed.set_image(url=card_data.get('image'))
    
    embed.set_footer(text=footer_text)
    
    return embed

def create_trace_embed(listing_data: dict, reason: str, snipe_details: dict = None):
    """
    Creates a simplified, crash-proof embed for Trace Logs (No Deal / Filtered).
    Handles missing keys gracefully.
    """
    # 1. Basic Data
    name = listing_data.get('name', 'Unknown Card')
    mint = listing_data.get('token_mint', 'N/A')
    
    # 2. Determine Color based on Status
    if "Rejected" in reason:
        color = 0xff0000  # Red (Filtered/Rejected)
        title = "❌ Rejected Listing"
    elif "No Deal" in reason:
        color = 0x808080  # Grey (No Deal)
        title = "📉 Processed: No Deal"
    else:
        color = 0xffffff  # White (Info)
        title = "🔍 Trace Info"

    # 3. Description Construction
    description = f"**Card**: {name}\n"
    description += f"**Reason**: {reason}\n\n"
    description += f"📍 **Mint**: `{mint}`\n"
    
    # 4. Create Embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    
    # Visual Polish: Use Fields
    if listing_data.get('price_amount'):
         embed.add_field(name="💰 Price", value=f"{listing_data.get('price_amount')} {listing_data.get('price_currency')}", inline=True)

    if snipe_details:
        alt_val = snipe_details.get('alt_value')
        avg_price = snipe_details.get('avg_price')
        
        val_str = f"${alt_val:.2f}" if alt_val else "N/A"
        avg_str = f"${avg_price:.2f}" if avg_price else "N/A"
        
        embed.add_field(name="Alt Value", value=val_str, inline=True)
        embed.add_field(name="Cartel Avg", value=avg_str, inline=True)
        
        if snipe_details.get('confidence'):
             embed.add_field(name="Conf", value=f"{snipe_details.get('confidence')}%", inline=True)

    if listing_data.get('token_mint'):
         embed.set_footer(text=f"Magic Eden Trace • {listing_data.get('token_mint')}")
    else:
         embed.set_footer(text="Magic Eden Trace")

    # 5. Add Thumbnail/Image if available
    img_url = listing_data.get('img_url') or listing_data.get('image')
    if img_url:
        embed.set_thumbnail(url=img_url)
    
    # 6. Add ME Link
    if mint != 'N/A':
        embed.url = f"https://magiceden.io/item-details/{mint}"

    return embed
