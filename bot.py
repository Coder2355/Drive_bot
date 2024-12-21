from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import base64
import os
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL, TARGET_CHANNEL
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999


app = Client("button_poster_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

poster_image = None
episode_data = {}

@app.on_message(filters.photo & filters.private)
async def add_poster(client, message):
    global poster_image
    poster_image = message.photo.file_id
    await message.reply_text("Poster image added successfully ✅")

@app.on_message(filters.video | filters.document & filters.private)
async def process_file(client, message):
    global poster_image, episode_data
    if not poster_image:
        await message.reply_text("Please set a poster image first by sending a photo.")
        return

    # Extract anime details
    file_name = message.video.file_name if message.video else message.document.file_name
    anime_name, episode_number, quality = parse_details(file_name)

    if not all([anime_name, episode_number, quality]):
        await message.reply_text("Failed to extract details. Make sure the file name is properly formatted.")
        return

    # Notify download
    await client.send_message(TARGET_CHANNEL, f"Downloading {quality} file...")

    # Download file
    download_path = await client.download_media(message)
    await client.send_message(TARGET_CHANNEL, f"Uploading {quality} file...")

    # Upload to file store channel
    sent_message = await client.send_document(FILE_STORE_CHANNEL, download_path)
    os.remove(download_path)  # Clean up

    # Generate base64 link
    file_id = sent_message.document.file_id
    link = base64.urlsafe_b64encode(file_id.encode()).decode()

    # Fetch bot's username
    bot_info = await client.get_me()
    bot_username = bot_info.username

    # Save the link and update qualities
    key = f"{anime_name}_EP{episode_number}"
    if key not in episode_data:
        episode_data[key] = {"anime_name": anime_name, "episode_number": episode_number, "qualities": {}}
    
    episode_data[key]["qualities"][quality] = f"https://t.me/{bot_username}?start={link}"
    buttons = [
        InlineKeyboardButton(
            f"{q}p", url=episode_data[key]["qualities"][q]
        ) for q in sorted(episode_data[key]["qualities"])
    ]
    keyboard = InlineKeyboardMarkup([buttons])

    # Send poster to target channel
    caption = (
        f"**{anime_name}**\n"
        f"**Episode:** {episode_number}\n"
        f"**Available Qualities:** {', '.join(sorted(episode_data[key]['qualities']))}"
    )
    await client.send_photo(TARGET_CHANNEL, poster_image, caption=caption, reply_markup=keyboard)
    

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) > 1:
        encoded_file_id = message.command[1]
        try:
            file_id = base64.urlsafe_b64decode(encoded_file_id).decode()
            await message.reply_document(file_id)
        except Exception:
            await message.reply_text("Invalid file link.")
    else:
        await message.reply_text("Welcome! Use this bot to manage anime uploads.")

def parse_details(file_name):
    """
    Parse anime details from file name.
    Expected format: AnimeName_EpisodeNumber_Quality.ext
    Example: Naruto_01_720p.mp4
    """
    try:
        parts = file_name.split("_")
        anime_name = parts[0]
        episode_number = parts[1].replace("EP", "").strip()
        quality = parts[2].split(".")[0]
        return anime_name, episode_number, quality
    except IndexError:
        return None, None, None

if __name__ == "__main__":
    app.run()
