import os
import base64
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL, TARGET_CHANNEL
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999



app = Client("button_poster_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global Variables
poster_image = None
episode_data = {}


# Utility Function: Parse File Details
def parse_details(file_name):
    try:
        parts = file_name.rsplit(".", 1)[0].split("-")
        anime_name = parts[0].strip()
        episode_number = parts[1].strip().replace("EP", "")
        quality = parts[2].strip().replace("p", "")
        return anime_name, episode_number, quality
    except:
        return None, None, None


# Poster Image Handler
@app.on_message(filters.photo & filters.private)
async def set_poster(client, message):
    global poster_image
    poster_image = await message.download()
    await message.reply_text("Poster image added successfully ✅")


# File Handler
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
    encoded_file_id = base64.urlsafe_b64encode(file_id.encode()).decode().strip("=")

    # Fetch bot's username
    bot_info = await client.get_me()
    bot_username = bot_info.username

    # Generate the correct link
    download_link = f"https://t.me/{bot_username}?start={encoded_file_id}"

    # Save the link and update qualities
    key = f"{anime_name}_EP{episode_number}"
    if key not in episode_data:
        episode_data[key] = {"anime_name": anime_name, "episode_number": episode_number, "qualities": {}}
    
    episode_data[key]["qualities"][quality] = download_link
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


# Start Command Handler
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) > 1:
        encoded_file_id = message.command[1]
        try:
            # Decode the file ID
            file_id = base64.urlsafe_b64decode(encoded_file_id + "=" * (-len(encoded_file_id) % 4)).decode()
            # Send the file to the user
            await message.reply_text("Fetching your file, please wait...")
            await client.send_document(message.chat.id, file_id)
        except Exception as e:
            await message.reply_text(f"Error: {e}\nThe file could not be retrieved. It may have been deleted.")
    else:
        await message.reply_text("Welcome! Send a file to use the bot.")


# Run the Bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
