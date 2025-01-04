
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


EPISODE_MESSAGES = {}  # Store episode numbers and their corresponding message IDs

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

    # Detect quality from caption
    quality = None
    if "480p" in message.caption:
        quality = "480p"
    elif "720p" in message.caption:
        quality = "720p"
    elif "1080p" in message.caption:
        quality = "1080p"

    if not quality:
        await message.reply_text("Please include quality (480p, 720p, 1080p) in the caption.")
        return

    # Update episode links
    if episode not in EPISODE_LINKS:
        EPISODE_LINKS[episode] = {}
    EPISODE_LINKS[episode][quality] = link

    # Create buttons dynamically based on available qualities
    buttons = []
    for q in ["480p", "720p", "1080p"]:
        if q in EPISODE_LINKS[episode]:
            buttons.append(InlineKeyboardButton(q, url=EPISODE_LINKS[episode][q]))

    # Send or edit the post in the target channel
    if len(buttons) > 0:
        if episode in EPISODE_MESSAGES:
            # Edit the existing message
            try:
                await client.edit_message_media(
                    TARGET_CHANNEL,
                    message_id=EPISODE_MESSAGES[episode],
                    media=pyrogram.types.InputMediaPhoto(
                        POSTER,
                        caption=f"Anime: You are MS Servant\nSeason: 01\nEpisode: {episode}\nQuality: {', '.join(EPISODE_LINKS[episode].keys())}\nLanguage: Tamil"
                    ),
                    reply_markup=InlineKeyboardMarkup([buttons]),
                )
                await message.reply_text("Episode updated successfully ✅")
            except Exception as e:
                await message.reply_text(f"Failed to edit the message: {e}")
        else:
            # Send a new message and store its message ID
            sent_message = await client.send_photo(
                TARGET_CHANNEL,
                photo=POSTER,
                caption=f"Anime: You are MS Servant\nSeason: 01\nEpisode: {episode}\nQuality: {', '.join(EPISODE_LINKS[episode].keys())}\nLanguage: Tamil",
                reply_markup=InlineKeyboardMarkup([buttons]),
            )
            EPISODE_MESSAGES[episode] = sent_message.id
            await message.reply_text("Episode posted successfully ✅")


# Start the bot
app.run()
