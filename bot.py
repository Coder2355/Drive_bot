from pyrogram import Client, filters
import os
import subprocess
import asyncio
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize bot with your credentials
app = Client(
    "audio_merge_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

AUDIO_DIR = os.getenv("AUDIO_DIR", "downloads")

# Global dictionary to store user sessions
user_sessions = {}

# Ensure the audio directory exists
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# Command to start the bot
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Send me two audio files, and I'll merge them for you!")

# Progress callback function
async def progress(current, total, progress_message: Message, task: str):
    try:
        progress_percentage = int(current * 100 / total)
        await progress_message.edit_text(f"{task}... {progress_percentage}%")
    except FloodWait as e:
        await asyncio.sleep(e.x)

# Function to download the audio file
async def download_audio(message, file_id, task_name):
    audio_path = os.path.join(AUDIO_DIR, f"{file_id}.mp3")
    progress_message = await message.reply_text(f"{task_name}...")
    await message.download(audio_path, progress=progress, progress_args=(progress_message, task_name))
    return audio_path

# Handle audio file or document audio file
@app.on_message(filters.audio | filters.document)
async def handle_audio(client, message):
    user_id = message.from_user.id
    file_id = message.audio.file_id if message.audio else message.document.file_id
    
    # Check if this is the first or second file
    if user_id not in user_sessions:
        # Store the first file
        user_sessions[user_id] = {
            "audio1": await download_audio(message, file_id, "Downloading first audio file")
        }
        await message.reply_text("First audio file received. Please send the second one.")
    else:
        # Store the second file and start the merging process
        user_sessions[user_id]["audio2"] = await download_audio(message, file_id, "Downloading second audio file")
        await merge_audios(client, message)

# Function to merge two audio files
async def merge_audios(client, message):
    user_id = message.from_user.id
    audio1 = user_sessions[user_id]["audio1"]
    audio2 = user_sessions[user_id]["audio2"]
    
    output_path = os.path.join(AUDIO_DIR, f"merged_{user_id}.mp3")
    
    # FFmpeg command to merge audios
    command = f"ffmpeg -i \"{audio1}\" -i \"{audio2}\" -filter_complex amerge -ac 2 -c:a libmp3lame -q:a 4 \"{output_path}\""
    
    try:
        subprocess.run(command, shell=True, check=True)
        uploading_msg = await message.reply_text("Uploading merged audio file...")
        await client.send_audio(message.chat.id, output_path, progress=progress, progress_args=(uploading_msg, "Uploading audio file"))
        await uploading_msg.edit_text("Here is your merged audio file.")
    except Exception as e:
        await message.reply_text(f"An error occurred while merging the audio files: {e}")
    
    # Clean up files
    os.remove(audio1)
    os.remove(audio2)
    os.remove(output_path)
    del user_sessions[user_id]

if __name__ == "__main__":
    app.run()
