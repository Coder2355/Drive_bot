from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize bot
bot = Client("episode_order_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store episodes
episodes = {}

@bot.on_message(filters.document | filters.video & ~filters.command(["order_episode"]))
async def receive_episode(client: Client, message: Message):
    """Handles the reception of episodes."""
    if not message.document and not message.video:
        await message.reply("Please send a valid video or document episode.")
        return

    # Extract filename or caption as episode identifier
    filename = message.document.file_name if message.document else message.video.file_name
    identifier = filename or f"Episode {len(episodes) + 1}"

    # Try to extract the episode number from filename
    try:
        episode_number = int("".join(filter(str.isdigit, filename)))
    except ValueError:
        await message.reply("Could not determine episode number from the file name.")
        return

    episodes[episode_number] = message
    await message.reply(f"{identifier} received as Episode {episode_number:02d}.")

@bot.on_message(filters.command("order_episode"))
async def order_episodes(client: Client, message: Message):
    """Sends episodes in order."""
    if not episodes:
        await message.reply("No episodes received yet!")
        return

    sorted_episodes = dict(sorted(episodes.items()))

    for episode_number, episode_message in sorted_episodes.items():
        await message.reply_document(
            document=episode_message.document.file_id if episode_message.document else episode_message.video.file_id,
            caption=f"Episode {episode_number:02d}"
        )

    # Clear episodes after sending
    episodes.clear()
    await message.reply("All episodes have been sent in order.")

if __name__ == "__main__":
    bot.run()
