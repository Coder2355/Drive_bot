import os
from pyrogram import Client, filters
from pyrogram.types import Message
import subprocess
from multiprocessing import Process
from flask import Flask, request

# Importing configuration from config.py
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize the bot client
app = Client("media_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize Flask web server
web_app = Flask(__name__)

# Directory to store the downloaded files
DOWNLOAD_DIR = "downloads/"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Store the file IDs temporarily for each user
user_media_files = {}

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text("Send me a video file and then an audio file to merge them, or send two audio files to merge them!")

@app.on_message((filters.video | filters.audio) & ~filters.forwarded)
async def receive_media(client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_media_files:
        user_media_files[user_id] = []

    media_type = 'audio' if message.audio else 'video'
    media_path = await message.download(file_name=f"{DOWNLOAD_DIR}{message.{media_type}.file_name}")

    user_media_files[user_id].append(media_path)

    if len(user_media_files[user_id]) == 1:
        if media_type == 'audio':
            await message.reply_text("First audio received. Now send the second audio.")
        else:
            await message.reply_text("Video received. Now send an audio file to merge with the video.")
    elif len(user_media_files[user_id]) == 2:
        if any('.mp4' in file for file in user_media_files[user_id]):
            await message.reply_text("Both media files received. Merging video with audio now...")
            await merge_video_and_audio(client, message, user_id)
        else:
            await message.reply_text("Both audios received. Merging them now...")
            await merge_audios(client, message, user_id)

async def merge_audios(client, message, user_id):
    audio1, audio2 = user_media_files[user_id]

    output_path = f"{DOWNLOAD_DIR}merged_audio_{user_id}.mp3"

    # FFmpeg command to merge the two audio files
    command = [
        "ffmpeg",
        "-i", audio1,
        "-i", audio2,
        "-filter_complex", "[0:0][1:0]concat=n=2:v=0:a=1[out]",
        "-map", "[out]",
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        await message.reply_audio(audio=output_path, caption="Here is your merged audio!")
    except subprocess.CalledProcessError as e:
        await message.reply_text(f"Failed to merge audios: {str(e)}")
    finally:
        # Clean up: remove the original audio files
        os.remove(audio1)
        os.remove(audio2)
        os.remove(output_path)
        del user_media_files[user_id]

async def merge_video_and_audio(client, message, user_id):
    video, audio = user_media_files[user_id]

    output_path = f"{DOWNLOAD_DIR}merged_video_{user_id}.mp4"

    # FFmpeg command to merge the video with the audio file
    command = [
        "ffmpeg",
        "-i", video,
        "-i", audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        await message.reply_video(video=output_path, caption="Here is your merged video!")
    except subprocess.CalledProcessError as e:
        await message.reply_text(f"Failed to merge video and audio: {str(e)}")
    finally:
        # Clean up: remove the original video and audio files
        os.remove(video)
        os.remove(audio)
        os.remove(output_path)
        del user_media_files[user_id]

@app.on_message(filters.command("cancel"))
async def cancel(client, message: Message):
    user_id = message.from_user.id
    if user_id in user_media_files:
        del user_media_files[user_id]
    await message.reply_text("Merging process has been cancelled.")

# Flask route for health check or any other web function
@web_app.route('/health')
def health_check():
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run()
