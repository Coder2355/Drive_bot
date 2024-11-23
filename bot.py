from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import os
from aiofiles import open as aio_open
from config import API_ID, API_HASH, BOT_TOKEN


app = Client(
    "EpisodeArrangerBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# In-memory storage for received episodes
episode_storage = {}

# Helper function to save episode
async def save_episode(file_id, file_name, episode_number):
    if not os.path.exists("episodes"):
        os.makedirs("episodes")
    file_path = f"episodes/{episode_number}_{file_name}"
    async with aio_open(file_path, "wb") as file:
        await app.download_media(file_id, file)
    return file_path

# Handler for receiving episodes
@app.on_message(filters.document | filters.video | filters.audio)
async def receive_episode(client, message: Message):
    user_id = message.from_user.id
    file_id = message.document.file_id if message.document else message.video.file_id if message.video else message.audio.file_id
    file_name = message.document.file_name if message.document else message.video.file_name if message.video else message.audio.file_name
    
    if user_id not in episode_storage:
        episode_storage[user_id] = []

    # Assign episode number
    episode_number = len(episode_storage[user_id]) + 1

    # Save episode metadata
    file_path = await save_episode(file_id, file_name, episode_number)
    episode_storage[user_id].append({"number": episode_number, "name": file_name, "path": file_path})

    await message.reply_text(f"Episode {episode_number} received: {file_name}")

# Handler for ordering episodes
@app.on_message(filters.command("order_episodes"))
async def order_episodes(client, message: Message):
    user_id = message.from_user.id

    if user_id not in episode_storage or not episode_storage[user_id]:
        await message.reply_text("No episodes received yet.")
        return

    # Sort episodes by their number
    episodes = sorted(episode_storage[user_id], key=lambda x: x["number"])

    # Send episodes back
    for episode in episodes:
        await message.reply_document(episode["path"], caption=f"Episode {episode['number']}: {episode['name']}")

    # Clear storage for user after sending
    del episode_storage[user_id]

# Start command
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "Welcome to the Episode Arranger Bot!\n\n"
        "1. Send me episodes one by one.\n"
        "2. Use /order_episodes to send all episodes back in order."
    )

# Run the bot
if __name__ == "__main__":
    app.run()
