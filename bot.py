from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import os
import base64
import pyrogram.utils

pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL, TARGET_CHANNEL

bot = Client("video_uploader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store episode data and uploaded qualities
episode_data = {}

@bot.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text(
        "Welcome to the Video Uploader Bot!\n\n"
        "Send a video to upload, or a picture to set as a poster.",
        quote=True
    )

@bot.on_message(filters.photo)
async def set_poster(_, message: Message):
    user_id = message.from_user.id
    episode_data[user_id] = {"poster": message.photo.file_id, "episodes": {}}
    sent_poster = await bot.send_photo(
        chat_id=TARGET_CHANNEL,
        photo=message.photo.file_id,
        caption="Poster image set successfully ✅"
    )
    episode_data[user_id]["poster_msg_id"] = sent_poster.message_id
    await message.reply_text("Poster image set successfully ✅", quote=True)

@bot.on_message(filters.video | filters.document)
async def process_video(_, message: Message):
    user_id = message.from_user.id
    if user_id not in episode_data or "poster" not in episode_data[user_id]:
        await message.reply_text("Please send a poster image first.", quote=True)
        return

    # Extract details from the video filename
    file_name = message.video.file_name if message.video else message.document.file_name
    anime_details = extract_anime_details(file_name)

    # Check if the episode already exists
    episodes = episode_data[user_id]["episodes"]
    episode_key = f"{anime_details['name']}_Ep{anime_details['episode']}"
    if episode_key not in episodes:
        episodes[episode_key] = {"qualities": {}, "poster_msg_id": None}

    # Check if the quality already exists
    quality = anime_details["quality"]
    if quality in episodes[episode_key]["qualities"]:
        await message.reply_text(f"{quality} already uploaded for this episode.", quote=True)
        return

    # Download and process the video
    await process_quality(message, user_id, anime_details, episodes, episode_key)

    # Update the poster with the new button
    await update_poster_buttons(message, user_id, anime_details, episodes, episode_key)

async def process_quality(message, user_id, anime_details, episodes, episode_key):
    quality = anime_details["quality"]
    download_msg = await bot.send_message(
        chat_id=TARGET_CHANNEL,
        text=f"Downloading {quality} file..."
    )
    file_path = await message.download()
    await bot.edit_message_text(
        chat_id=TARGET_CHANNEL,
        message_id=download_msg.message_id,
        text=f"{quality} file downloaded successfully ✅"
    )

    # Upload file to file store channel
    store_msg = await bot.send_message(
        chat_id=TARGET_CHANNEL,
        text=f"Uploading {quality} file to file store channel..."
    )
    sent_message = await bot.send_document(FILE_STORE_CHANNEL, file_path)
    os.remove(file_path)
    await bot.edit_message_text(
        chat_id=TARGET_CHANNEL,
        message_id=store_msg.message_id,
        text=f"{quality} file uploaded to file store channel ✅"
    )

    # Generate sharable link
    file_id = sent_message.document.file_id
    sharable_link = generate_file_store_link(file_id)

    # Store the link
    episodes[episode_key]["qualities"][quality] = sharable_link

async def update_poster_buttons(message, user_id, anime_details, episodes, episode_key):
    # Get existing poster message ID
    poster_id = episode_data[user_id]["poster"]
    poster_msg_id = episodes[episode_key]["poster_msg_id"]

    # Generate updated buttons
    qualities = episodes[episode_key]["qualities"]
    buttons = [
        [InlineKeyboardButton(q, url=link)] for q, link in qualities.items()
    ]

    # Update or send the poster
    if poster_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=TARGET_CHANNEL,
                message_id=poster_msg_id,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            print(f"Failed to edit poster: {e}")
    else:
        sent_poster = await bot.send_photo(
            chat_id=TARGET_CHANNEL,
            photo=poster_id,
            caption=f"**Anime Name:** {anime_details['name']}\n"
                    f"**Episode:** {anime_details['episode']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        episodes[episode_key]["poster_msg_id"] = sent_poster.message_id

def extract_anime_details(file_name: str) -> dict:
    # Example logic to extract details from filename
    parts = file_name.split("_")
    return {
        "name": parts[0].replace("-", " ").title(),
        "episode": parts[1].replace("Ep", ""),
        "quality": parts[2].replace(".mp4", "")
    }

def generate_file_store_link(file_id: str) -> str:
    # Generate a sharable link using base64 encoding
    base_url = "https://t.me/"
    encoded_id = base64.urlsafe_b64encode(file_id.encode()).decode()
    return f"{base_url}{encoded_id}"

if __name__ == "__main__":
    bot.run()
