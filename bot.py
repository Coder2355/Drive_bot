from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import os
from config import API_ID, API_HASH, BOT_TOKEN


bot = Client(
    "EpisodeArrangerBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# Temporary storage for episode files
episode_files = {}

# Command to order episodes
@bot.on_message(filters.command("order_episodes") & filters.private)
async def order_episodes(_, message: Message):
    await message.reply(
        "Please send all the episode files. Once you're done, use the `/done` command to arrange them.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Done", callback_data="done_ordering")]
        ]),
    )
    episode_files[message.chat.id] = []

# Handle incoming files
@bot.on_message(filters.document | filters.video)
async def collect_episodes(_, message: Message):
    if message.chat.id not in episode_files:
        return await message.reply("Please start by using the `/order_episodes` command.")
    
    episode_files[message.chat.id].append(message)
    await message.reply(f"Added: `{message.document.file_name or message.video.file_name}`")

# Handle done command
@bot.on_message(filters.command("done") & filters.private)
async def finalize_order(_, message: Message):
    if message.chat.id not in episode_files or not episode_files[message.chat.id]:
        return await message.reply("No episodes were sent. Please send files first.")

    # Sort files by episode number in the name
    files = episode_files[message.chat.id]
    try:
        files.sort(key=lambda x: int(''.join(filter(str.isdigit, x.document.file_name or x.video.file_name))))
    except ValueError:
        return await message.reply("Couldn't determine episode numbers. Ensure filenames contain numbers.")

    await message.reply("Arranged Episodes in Order:\n" + "\n".join(
        f"{i + 1}. {file.document.file_name or file.video.file_name}" for i, file in enumerate(files)
    ))
    
    # Reset for the user
    del episode_files[message.chat.id]

# Callback for done ordering
@bot.on_callback_query(filters.regex("done_ordering"))
async def done_ordering(_, callback_query):
    await finalize_order(callback_query.message)

if __name__ == "__main__":
    bot.run()
