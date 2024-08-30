import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize the Pyrogram client
app = Client("audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to keep track of users who are merging audio
merger = {}

# Function to download files
async def download_file(message, file_name):
    file_path = await message.download(file_name)
    return file_path

# Function to merge two audio files using FFmpeg
async def merge_audio_files(file1, file2, output_file):
    (
        ffmpeg
        .input(file1)
        .input(file2)
        .filter('amix', inputs=2)
        .output(output_file)
        .run(overwrite_output=True)
    )

# Command handler for /merge_audio
@app.on_message(filters.command("merge_audio") & filters.reply)
async def merge_audio_command(client, message):
    # Check if the replied message is an audio file or audio document
    if not (message.reply_to_message.audio or message.reply_to_message.document):
        await message.reply_text("Please reply to an audio file or audio document.")
        return

    # Show inline keyboard to start the merge process
    buttons = [
        [InlineKeyboardButton("audio+audio", callback_data="start_merge")]
    ]
    await message.reply_text("Press the button to start merging the audio files:", reply_markup=InlineKeyboardMarkup(buttons))
    
    # Store the user's ID and the first audio file
    merger[message.from_user.id] = {"first_audio": message.reply_to_message}

# Callback query handler for the inline keyboard
@app.on_callback_query(filters.regex("start_merge"))
async def on_start_merge(client, callback_query):
    user_id = callback_query.from_user.id
    
    if user_id not in merger:
        await callback_query.message.reply_text("Please start the process by replying to an audio file with /merge_audio.")
        return
    
    await callback_query.message.edit_text("Please send the second audio file.")

# Handler for receiving the second audio file
@app.on_message(filters.audio | filters.document)
async def receive_second_audio(client, message):
    user_id = message.from_user.id
    
    # Check if the user is in the merging process
    if user_id not in merger:
        return
    
    # Get the first audio message and download both audio files
    first_audio = merger[user_id]["first_audio"]
    first_file_name = f"{user_id}_first_audio.mp3"
    second_file_name = f"{user_id}_second_audio.mp3"
    output_file_name = f"{user_id}_merged_audio.mp3"
    
    await message.reply_text("Downloading audio files...")

    first_file_path = await download_file(first_audio, first_file_name)
    second_file_path = await download_file(message, second_file_name)

    await message.reply_text("Merging audio files...")

    # Merge the audio files
    await merge_audio_files(first_file_path, second_file_path, output_file_name)
    
    # Send the merged audio file
    await message.reply_audio(audio=output_file_name, caption="Here is your merged audio file!")

    # Clean up the temporary files
    os.remove(first_file_path)
    os.remove(second_file_path)
    os.remove(output_file_name)
    
    # Remove the user from the merger dictionary
    del merger[user_id]

# Start the bot
app.run()
