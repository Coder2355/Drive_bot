import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL

app = Client("button_poster_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

POSTER = None  # To store the poster image
POSTERS = {}  # Dictionary to track poster buttons (anime name -> [quality buttons])
PROTECT_CONTENT = False
CUSTOM_CAPTION = None
DISABLE_CHANNEL_BUTTON = False


# Helper Functions
async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").strip("=")
    return base64_string


async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string


async def present_user(user_id):
    # Dummy function to check user presence in the database
    return False


async def add_user(user_id):
    # Dummy function to add a user to the database
    pass


async def get_messages(client, ids):
    db_channel = await client.get_chat(FILE_STORE_CHANNEL)
    messages = []
    for message_id in ids:
        message = await client.get_messages(chat_id=db_channel.id, message_ids=message_id)
        messages.append(message)
    return messages


# Commands
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    if not await present_user(id):
        try:
            await add_user(id)
        except:
            pass

    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except:
            return
        string = await decode(base64_string)
        argument = string.split("-")
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except:
                return
            if start <= end:
                ids = range(start, end + 1)
            else:
                ids = []
                i = start
                while True:
                    ids.append(i)
                    i -= 1
                    if i < end:
                        break
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except:
                return
        temp_msg = await message.reply("Please wait...")
        try:
            messages = await get_messages(client, ids)
        except:
            await message.reply_text("Something went wrong..!")
            return
        await temp_msg.delete()

        for msg in messages:
            if bool(CUSTOM_CAPTION) and bool(msg.document):
                caption = CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name,
                )
            else:
                caption = "" if not msg.caption else msg.caption.html

            if DISABLE_CHANNEL_BUTTON:
                reply_markup = msg.reply_markup
            else:
                reply_markup = None

            try:
                await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT,
                )
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT,
                )
            except:
                pass
        return

    await message.reply_text("Welcome to the Button Poster Upload Bot!\nSend a picture to set the poster and videos/documents to process.")


@app.on_message(filters.photo & filters.private)
async def set_poster(client: Client, message: Message):
    global POSTER
    POSTER = message.photo.file_id
    await message.reply_text("Poster image added successfully ✅")


@app.on_message(filters.video | filters.document)
async def process_file(client: Client, message: Message):
    global POSTER
    if not POSTER:
        await message.reply_text("Please set a poster image first!")
        return

    # Extract details from the file name
    file_name = message.video.file_name if message.video else message.document.file_name
    parts = file_name.split("_")
    if len(parts) < 3:
        await message.reply_text("Invalid file naming format! Expected format: `AnimeName_Episode_Quality`")
        return

    anime_name, episode, quality = parts[0], parts[1], parts[2].split(".")[0]
    target_channel = FILE_STORE_CHANNEL

    # Send poster with buttons
    buttons = POSTERS.get(anime_name, [])
    if quality not in buttons:
        buttons.append(quality)
        POSTERS[anime_name] = buttons

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"{btn}p", callback_data=f"view_{anime_name}_{btn}")] for btn in buttons]
    )

    await client.send_photo(
        chat_id=target_channel,
        photo=POSTER,
        caption=f"Anime: {anime_name}\nEpisode: {episode}\nQuality: {quality}",
        reply_markup=markup,
    )

    # Download the video
    status_msg = await client.send_message(target_channel, f"Downloading {quality} file...")
    downloaded_file = await message.download()
    await status_msg.edit_text("File downloaded successfully!")

    # Upload file to file store channel
    db_channel = await client.get_chat(FILE_STORE_CHANNEL)
    try:
        post_message = await client.send_document(chat_id=db_channel.id, document=downloaded_file)
    except Exception as e:
        await client.send_message(target_channel, "Failed to upload the file!")
        print(e)
        return

    # Generate link
    converted_id = post_message.id * abs(db_channel.id)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    # Update poster with link
    await client.send_message(target_channel, f"Uploading {quality} file completed!\nFile link: {link}")


@app.on_callback_query(filters.regex(r"^view_(.+)_(\d+)p$"))
async def send_file(client: Client, callback_query):
    data = callback_query.data.split("_")
    anime_name, quality = data[1], data[2]
    await callback_query.answer(f"Redirecting to {quality}p file...")
    await callback_query.message.reply_text(f"Please wait...\nFetching {quality}p file for {anime_name}...")

    # Decode link and send file (placeholder response for now)
    await callback_query.message.reply_text("This functionality is under development!")


if __name__ == "__main__":
    app.run()
