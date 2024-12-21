import asyncio
import re
import base64
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL, TARGET_CHANNEL
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999


app = Client("button_poster_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

poster = None  # Global variable to store the poster image

# Base64 Encoding and Decoding
async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return (base64_bytes.decode("ascii")).strip("=")

async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    return string_bytes.decode("ascii")

@app.on_message(filters.photo & filters.private)
async def set_poster(client, message: Message):
    global poster
    poster = message.photo.file_id
    await message.reply("Poster added successfully ✅")

@app.on_message(filters.video | filters.document & filters.private)
async def process_file(client, message: Message):
    global poster
    if not poster:
        await message.reply("❌ Please set a poster first by sending a photo.")
        return

    # Extract file details
    file_name = message.document.file_name if message.document else message.video.file_name
    anime_name, episode, quality = extract_details(file_name)
    
    if not (anime_name and episode and quality):
        await message.reply("❌ Could not extract details from the file name.")
        return

    # Send poster with details to the target channel
    buttons = [[InlineKeyboardButton(f"{quality}p", callback_data=f"get_link_{quality}")]]
    caption = f"**Anime Name:** {anime_name}\n**Episode:** {episode}\n**Quality:** {quality}p"
    await client.send_photo(
        chat_id=TARGET_CHANNEL,
        photo=poster,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await message.reply(f"Downloading the {quality} file...")

    # Download file
    file_path = await message.download()

    # Upload to file store channel
    file_message = await client.send_document(chat_id=FILE_STORE_CHANNEL, document=file_path)
    msg_id = file_message.id

    # Generate link
    base64_string = await encode(f"get-{msg_id * abs(client.FILE_STORE_CHANNEL.id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"

    # Update poster with additional quality buttons
    await update_poster(client, anime_name, episode, quality, link)

    await message.reply(f"Uploading the {quality} file completed ✅")

async def update_poster(client, anime_name, episode, quality, link):
    messages = await client.get_messages(chat_id=TARGET_CHANNEL)
    for msg in messages:
        if anime_name in msg.caption and f"Episode: {episode}" in msg.caption:
            buttons = msg.reply_markup.inline_keyboard
            new_button = InlineKeyboardButton(f"{quality}p", url=link)
            buttons.append([new_button])
            await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
            break

def extract_details(file_name):
    try:
        parts = file_name.split("-")
        anime_name = parts[0].strip()
        episode = re.search(r"E(\d+)", parts[1]).group(1)
        quality = re.search(r"(\d+)p", parts[2]).group(1)
        return anime_name, episode, quality
    except:
        return None, None, None

@app.on_callback_query()
async def handle_callback(client, callback_query):
    data = callback_query.data
    if data.startswith("get_link_"):
        quality = data.split("_")[2]
        await callback_query.message.reply(f"Here is your {quality}p file link: {callback_query.message.reply_markup.inline_keyboard[0][0].url}")

if __name__ == "__main__":
    app.run()
