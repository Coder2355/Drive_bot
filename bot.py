from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import asyncio
import ffmpeg
import time
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize the bot with your credentials
app = Client("audio_converter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store file paths
user_files = {}

# Function to convert audio
async def convert_audio(file_path, output_format):
    output_file = f"{os.path.splitext(file_path)[0]}.{output_format}"
    await asyncio.create_subprocess_shell(
        f"ffmpeg -i {file_path} {output_file}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return output_file

# Progress function
async def progress_for_pyrogram(current, total, message, action):
    try:
        percentage = current * 100 / total
        progress = f"[{'█' * int(percentage / 5)}{'░' * (20 - int(percentage / 5))}]"
        await message.edit_text(f"{action}\n{progress} {percentage:.1f}%")
    except Exception as e:
        print(e)

# Command handler for /convert_audio
@app.on_message(filters.command("convert_audio") & (filters.reply | filters.audio | filters.document))
async def convert_audio_command(client, message):
    sent_msg = await message.reply_text("Downloading...")

    # Download the replied audio file with progress tracking
    file = await client.download_media(
        message.reply_to_message.audio or message.reply_to_message.document,
        progress=progress_for_pyrogram,
        progress_args=(sent_msg, "Downloading...")
    )
    
    # Store the file path in the user's state (using message ID as a key)
    user_files[message.from_user.id] = file
    
    # Create inline keyboard for format selection
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("MP3", callback_data="mp3"),
         InlineKeyboardButton("AAC", callback_data="aac")],
        [InlineKeyboardButton("Opus", callback_data="opus"),
         InlineKeyboardButton("OGG", callback_data="ogg")],
        [InlineKeyboardButton("WAV", callback_data="wav"),
         InlineKeyboardButton("AC3", callback_data="ac3")],
        [InlineKeyboardButton("M4A", callback_data="m4a"),
         InlineKeyboardButton("Cancel", callback_data="cancel")]
    ])
    
    # Send message with inline keyboard
    await sent_msg.edit_text("Choose the output format:", reply_markup=keyboard)

# Callback query handler for format selection
@app.on_callback_query()
async def callback_query_handler(client, callback_query):
    user_id = callback_query.from_user.id
    file = user_files.get(user_id)

    if not file:
        await callback_query.message.edit_text("No file found to convert.")
        return

    if callback_query.data == "cancel":
        await callback_query.message.edit_text("Conversion canceled.")
        os.remove(file)
        user_files.pop(user_id, None)
        return

    output_format = callback_query.data
    await callback_query.message.edit_text(f"Converting to {output_format}...")

    # Convert the audio file
    output_file = await convert_audio(file, output_format)
    
    # Upload the converted file with progress tracking
    sent_msg = await callback_query.message.edit_text("Uploading...")
    await client.send_audio(
        chat_id=callback_query.message.chat.id, 
        audio=output_file,
        progress=progress_for_pyrogram,
        progress_args=(sent_msg, "Uploading...")
    )

    # Clean up
    os.remove(file)
    os.remove(output_file)
    user_files.pop(user_id, None)

# Run the bot
app.run()
