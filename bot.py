from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
import os

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

    # Extract the original filename
    filename = message.document.file_name if message.document else message.video.file_name

    # Try to extract the episode number from the filename
    try:
        episode_number = int("".join(filter(str.isdigit, filename.split()[0])))
    except ValueError:
        await message.reply("Could not determine episode number from the file name.")
        return

    # Store the message and filename in the dictionary
    episodes[episode_number] = {"message": message, "filename": filename}
    await message.reply(f"Episode {episode_number} received.")

@bot.on_message(filters.command("order_episode"))
async def order_episodes(client: Client, message: Message):
    """Sends episodes in order."""
    if not episodes:
        await message.reply("No episodes received yet!")
        return

    # Sort episodes by their episode number
    sorted_episodes = dict(sorted(episodes.items()))

    for episode_number, data in sorted_episodes.items():
        episode_message = data["message"]
        filename = data["filename"]

        # Temporarily download the file and send it back with the correct name
        temp_file_path = await episode_message.download()

        try:
            # Rename and send the file with the original filename
            correct_filename = filename
            os.rename(temp_file_path, correct_filename)

            # Send the renamed file
            if episode_message.document:
                await message.reply_document(
                    document=correct_filename,
                    caption=filename
                )
            elif episode_message.video:
                await message.reply_video(
                    video=correct_filename,
                    caption=filename
                )
        finally:
            # Clean up the file after sending
            if os.path.exists(correct_filename):
                os.remove(correct_filename)

    # Clear episodes after sending
    episodes.clear()
    await message.reply("All episodes have been sent in order.")

if __name__ == "__main__":
    bot.run()
