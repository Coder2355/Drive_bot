import base64
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL, TARGET_CHANNEL
# Bot configuration

# Channel IDs
STORE_CHANNEL = FILE_STORE_CHANNEL  # Replace with your store channel ID

# Initialize the bot
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global dictionary to store episode links and poster
POSTER = None
EPISODE_LINKS = {}


# Helper to encode file ID
def encode_file_id(file_id):
    return base64.urlsafe_b64encode(file_id.encode()).decode()


# Handle poster upload
@app.on_message(filters.photo & ~filters.channel)
async def handle_poster(client, message):
    global POSTER
    POSTER = message.photo.file_id
    await message.reply_text("Poster added successfully ✅")


# Handle video and document upload
@app.on_message((filters.video | filters.document) & ~filters.channel)
async def handle_media(client, message):
    global POSTER

    if POSTER is None:
        await message.reply_text("Please upload a poster first by sending a photo.")
        return

    # Extract episode info from caption (e.g., "Episode : 10")
    if not message.caption or "Episode :" not in message.caption:
        await message.reply_text("Please include 'Episode : <number>' in the caption.")
        return

    # Get the episode number
    try:
        episode = message.caption.split("Episode :")[1].split()[0].strip()
    except IndexError:
        await message.reply_text("Invalid episode format. Use 'Episode : <number>'.")
        return

    # Forward file to the store channel
    forwarded = await message.forward(STORE_CHANNEL)
    file_id = forwarded.id
    encoded_id = encode_file_id(str(file_id))

    # Generate a download link for the forwarded file
    link = f"https://t.me/{STORE_CHANNEL}/{file_id}?id={encoded_id}"

    # Add link to the episode dictionary
    if episode not in EPISODE_LINKS:
        EPISODE_LINKS[episode] = {}

    # Detect quality and add link
    if "480p" in message.caption:
        EPISODE_LINKS[episode]["480p"] = link
    elif "720p" in message.caption:
        EPISODE_LINKS[episode]["720p"] = link
    elif "1080p" in message.caption:
        EPISODE_LINKS[episode]["1080p"] = link
    else:
        await message.reply_text("Please include quality (480p, 720p, 1080p) in the caption.")
        return

    # Create buttons
    buttons = []
    if "480p" in EPISODE_LINKS[episode]:
        buttons.append(InlineKeyboardButton("480p", url=EPISODE_LINKS[episode]["480p"]))
    if "720p" in EPISODE_LINKS[episode]:
        buttons.append(InlineKeyboardButton("720p", url=EPISODE_LINKS[episode]["720p"]))
    if "1080p" in EPISODE_LINKS[episode]:
        buttons.append(InlineKeyboardButton("1080p", url=EPISODE_LINKS[episode]["1080p"]))

    # Send to the target channel
    await client.send_photo(
        TARGET_CHANNEL,
        photo=POSTER,
        caption=f"Anime: You are MS Servant\nSeason: 01\nEpisode: {episode}\nLanguage: Tamil",
        reply_markup=InlineKeyboardMarkup([buttons]),
    )

    await message.reply_text("Episode posted successfully ✅")


# Start the bot
app.run()
