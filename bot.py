import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import ffmpeg
from flask import Flask
import threading
import aiofiles
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIR

# Initialize the Pyrogram Client
app = Client("audio_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize Flask app
flask_app = Flask(__name__)

# Dictionary to store user states
user_states = {}

async def run_ffmpeg_command(*args):
    process = await asyncio.create_subprocess_exec(
        'ffmpeg', *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"FFmpeg error: {stderr.decode()}")

@app.on_message(filters.command("trim_audio"))
async def trim_audio(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.audio:
        await message.reply("Please reply to an audio message with the command /trim_audio start_time end_time")
        return

    command_parts = message.text.split()
    if len(command_parts) != 3:
        await message.reply("Usage: /trim_audio start_time end_time (e.g., /trim_audio 00:00:10 00:00:20)")
        return

    start_time, end_time = command_parts[1], command_parts[2]
    audio_file = await message.reply_to_message.download(DOWNLOAD_DIR)

    status_message = await message.reply("Trimming audio...")

    trimmed_file = os.path.join(DOWNLOAD_DIR, "trimmed_" + os.path.basename(audio_file))

    try:
        await run_ffmpeg_command('-i', audio_file, '-ss', start_time, '-to', end_time, '-c', 'copy', trimmed_file)
        await status_message.edit("Uploading trimmed audio...")
        await message.reply_audio(audio=trimmed_file)
        await status_message.delete()
    except Exception as e:
        await status_message.edit(f"An error occurred: {e}")
    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)
        if os.path.exists(trimmed_file):
            os.remove(trimmed_file)

@app.on_message(filters.command("merge_audio"))
async def start_merge_audio(client: Client, message: Message):
    await message.reply("Please send the first audio file.")
    user_states[message.from_user.id] = {"state": "waiting_for_first_audio"}

@app.on_message(filters.audio)
async def handle_audio(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_states:
        return

    state = user_states[user_id].get("state")

    if state == "waiting_for_first_audio":
        status_message = await message.reply("Downloading first audio...")
        first_audio_file = await message.download(DOWNLOAD_DIR)
        await status_message.edit("First audio received. Please send the second audio file.")
        user_states[user_id] = {"state": "waiting_for_second_audio", "first_audio_file": first_audio_file}
    elif state == "waiting_for_second_audio":
        first_audio_file = user_states[user_id]["first_audio_file"]
        
        status_message = await message.reply("Downloading second audio...")
        second_audio_file = await message.download(DOWNLOAD_DIR)
        await status_message.edit("Merging audio files...")

        merged_file = os.path.join(DOWNLOAD_DIR, "merged_audio.mp3")

        try:
            await run_ffmpeg_command('-i', first_audio_file, '-i', second_audio_file, '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[out]', '-map', '[out]', merged_file)
            await status_message.edit("Uploading merged audio...")
            await message.reply_audio(audio=merged_file)
            await status_message.delete()
        except Exception as e:
            await status_message.edit(f"An error occurred: {e}")
        finally:
            if os.path.exists(first_audio_file):
                os.remove(first_audio_file)
            if os.path.exists(second_audio_file):
                os.remove(second_audio_file)
            if os.path.exists(merged_file):
                os.remove(merged_file)

        # Clear the user's state
        del user_states[user_id]

@flask_app.route('/')
def index():
    return "Bot is running"

app.run()
