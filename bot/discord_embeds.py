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

def create_snipe_embed(listing_data: dict, snipe_details: dict, alert_level: str, duration: float = 0.0):
    """
    Creates a rich discord.Embed object based on the new design.
    """
    footer_icon = "https://emoji.discadia.com/emojis/7b975e64-50d6-4710-a49f-e55bc1e629e2.png"
    if alert_level.upper() == 'GOLD':
        color = 0xffd700  # Gold
        footer_text = "AUTOBUY SNIPE"
    elif alert_level.upper() == 'HIGH':
        color = 0xff0000  # Red
        footer_text = "HIGH ALERT SNIPE"
    else:
        color = 0x0099ff # Blue
        footer_text = "INFO"

    # Append duration to the footer text
    if duration > 0:
        footer_text += f" | Processed in {duration:.2f}s"

    me_link = f"https://magiceden.io/item-details/{listing_data.get('token_mint')}"
    cc_link = f"https://collectorcrypt.com/assets/solana/{listing_data.get('token_mint')}"
    alt_link = f"https://app.alt.xyz/research/{snipe_details.get('alt_asset_id')}" if snipe_details.get('alt_asset_id') else "https://app.alt.xyz/"

    # --- Construct the Multi-line Description ---
    description = (
        f"📍 Mint: ```{listing_data.get('token_mint')}```"
        f"🏢 Grading Company: **`{listing_data.get('grading_company')}`**\n"
        f"🆔 Grading ID: **`{listing_data.get('grading_id')}`**\n"
        f"🈴 Grade: **`{listing_data.get('grade')}`**\n"
        f"{DOLLAR_EMOTE} Insured Value: {USDC_EMOTE} **`{listing_data.get('insured_value'):.2f}`**\n"        
        f"#️⃣ Supply: **`{snipe_details.get('supply', 'N/A')}`**\n\n"
        f"{ALT_EMOTE} [ALT.XYZ]({alt_link})\n"
        f"{ME_EMOTE} [Magic Eden]({me_link})\n"
        f"{CC_EMOTE} [Collector Crypt]({cc_link})\n"
    )
    
    # --- Create the Embed ---
    embed = discord.Embed(
        title=listing_data.get('name', "Unknown"),
        url=me_link,
        description=description,
        color=color,
    )

    # --- Add Inline Fields for Stats ---
    currency_emote = SOL_EMOTE if listing_data.get('price_currency') == 'SOL' else USDC_EMOTE
    embed.add_field(name=f"{ME_EMOTE} Listed Price", value=f"{currency_emote} {listing_data.get(f'price_amount', 0):.4f}\n*({USDC_EMOTE} {snipe_details.get('listing_price_usd', 0):.2f})*", inline=True)
    embed.add_field(name="Difference", value=snipe_details['difference_str'], inline=True)
    embed.add_field(name=f"Cartel AVG", value=f"{USDC_EMOTE} {snipe_details.get('avg_price', 0):.2f}", inline=True)
    embed.add_field(name=f"Alt Value", value=f"{USDC_EMOTE} {snipe_details.get('alt_value', 0):.2f}", inline=True)
    embed.add_field(name="ALT Confidence", value=f"{snipe_details.get('confidence', 0)}%", inline=True)
    embed.add_field(name="ALT Value Range", value=f"{USDC_EMOTE} {snipe_details.get('lower_bound', 0):.2f} - {snipe_details.get('upper_bound', 0):.2f}", inline=True)

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
