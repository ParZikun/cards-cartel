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

def create_snipe_embed(listing_data: dict, snipe_details: dict, alert_level: str):
    """
    Creates a rich discord.Embed object based on the new design.
    """
    footer_icon = "https://emoji.discadia.com/emojis/7b975e64-50d6-4710-a49f-e55bc1e629e2.png"
    if alert_level.upper() == 'HIGH':
        color = 0xff0000  # Red
        footer_text = "HIGH ALERT SNIPE"
    else:
        color = 0x0099ff # Blue
        footer_text = "INFO"

    me_link = f"https://magiceden.io/item-details/{listing_data.get('token_mint')}"
    cc_link = f"https://collectorcrypt.com/assets/solana/{listing_data.get('token_mint')}"
    alt_link = f"https://app.alt.xyz/research/{snipe_details.get('alt_asset_id')}" if snipe_details.get('alt_asset_id') else "https://app.alt.xyz/"

    listing_price_usd = snipe_details.get('listing_price_usd', 0)
    alt_value = snipe_details.get('alt_value', 0)
    difference_str = "N/A"
    if alt_value > 0 and listing_price_usd > 0:
        difference_percent = ((listing_price_usd - alt_value) / alt_value) * 100
        # Add a green circle if it's a significant discount
        if difference_percent <= -50:
            difference_str = f"🟢 **{difference_percent:.2f}%**"
        else:
            difference_str = f"{difference_percent:+.2f}%" # Show + or - sign

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
    embed.add_field(name=f"{ME_EMOTE} Listed Price", value=f"{currency_emote} {listing_data.get(f'price_amount', 0):.4f}\n*({USDC_EMOTE} {listing_price_usd:.2f})*", inline=True)
    embed.add_field(name="Difference", value=difference_str, inline=True)
    embed.add_field(name=f"Cartel AVG", value=f"{USDC_EMOTE} {snipe_details.get('avg_price', 0):.2f}", inline=True)
    embed.add_field(name=f"Alt Value", value=f"{USDC_EMOTE} {snipe_details.get('alt_value', 0):.2f}", inline=True)
    embed.add_field(name="ALT Confidence", value=f"{snipe_details.get('confidence', 0)}%", inline=True)
    embed.add_field(name="ALT Value Range", value=f"{USDC_EMOTE} {snipe_details.get('lower_bound', 0):.2f} - {snipe_details.get('upper_bound', 0):.2f}", inline=True)

    if listing_data.get('img_url'):
        embed.set_image(url=listing_data.get('img_url'))
    
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    
    return embed
