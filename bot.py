from pyrogram import Client, filters
from pyrogram.types import Message
import re

from config import API_ID, API_HASH, BOT_TOKEN
# Initialize bot
bot = Client("episode_order_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to temporarily store episode messages
episode_storage = {}

# Custom filter to exclude command messages
def is_not_command(_, __, message: Message):
    return not message.text or not message.text.startswith("/")

@bot.on_message(filters.private & filters.document & filters.create(is_not_command))
async def collect_episodes(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in episode_storage:
        episode_storage[user_id] = []
    
    # Save the document message ID for reference
    episode_storage[user_id].append((message.message_id, message.document.file_name))
    await message.reply_text(f"Added: `{message.document.file_name}`\nSend `/order_episodes` to arrange them.", quote=True)

@bot.on_message(filters.private & filters.command("order_episodes"))
async def order_episodes(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in episode_storage or not episode_storage[user_id]:
        await message.reply_text("No episodes found! Please send the episodes first.", quote=True)
        return

    # Extract file names and sort them
    episodes = episode_storage[user_id]
    sorted_episodes = sorted(episodes, key=lambda x: extract_episode_number(x[1]))

    # Prepare response message
    response = "**Ordered Episodes:**\n"
    for i, (_, file_name) in enumerate(sorted_episodes, start=1):
        response += f"{i}. `{file_name}`\n"

    # Send the ordered list
    await message.reply_text(response)

    # Reset storage for the user
    episode_storage[user_id] = []

def extract_episode_number(file_name):
    """
    Extracts the episode number from the file name using a regex.
    If no number is found, returns a very high value to sort it at the end.
    """
    match = re.search(r"(\d+)", file_name)
    return int(match.group(1)) if match else float("inf")

@bot.on_message(filters.private & filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text(
        "Hello! I am an Episode Order Bot.\n\n"
        "1. Send me all the episodes as document files.\n"
        "2. Use the `/order_episodes` command to get them arranged in order.\n\n"
        "Enjoy organizing your episodes effortlessly!"
    )

# Run the bot
bot.run()
