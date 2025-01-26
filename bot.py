import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from time import time
from math import floor
from pyrogram.errors import FloodWait

from config import API_ID, API_HASH, BOT_TOKEN

app = Client("compress_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to extract FFmpeg progress and report encoding status
async def compress_video(input_file, output_file, duration, original_size, progress_callback):
    start_time = time()
    last_update_time = 0  # To throttle updates
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", input_file,
        "-vf", "scale=-1:240",  # Scale to 240p
        "-c:v", "libx264",  # Use H.264 codec
        "-preset", "fast",  # Set compression speed
        "-crf", "28",  # Quality factor
        "-c:a", "aac",  # Audio codec
        "-b:a", "64k",  # Audio bitrate
        "-progress", "pipe:1",  # Output progress to pipe
        "-y",  # Overwrite output
        output_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    current_time = 0
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        line = line.decode().strip()
        if "=" in line:
            key, value = line.split("=", 1)
            if key == "out_time_us":
                current_time = int(value) / 1_000_000  # Convert microseconds to seconds
                percentage = (current_time / duration) * 100 if duration else 0

                # Read the actual current file size
                current_file_size = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0

                # Estimate final size based on progress
                estimated_size = current_file_size / (percentage / 100) if percentage > 0 else original_size

                # Throttle progress updates to every 5 seconds
                if time() - last_update_time > 5:
                    await progress_callback(percentage, current_file_size, estimated_size, start_time)
                    last_update_time = time()

    await process.wait()

# Function to update progress
async def progress_handler(message, percentage, current_size, estimated_size, start_time):
    elapsed_time = time() - start_time
    progress_bar = "▓" * floor(percentage / 10) + "░" * (10 - floor(percentage / 10))
    progress_message = (
        f"🎥 **Encoding Progress**:\n"
        f"**[{progress_bar}]** {percentage:.2f}%\n"
        f"**Elapsed Time**: {elapsed_time:.2f} seconds\n"
        f"**Current File Size**: {current_size:.2f} MB\n"
        f"**Estimated Final Size**: {estimated_size:.2f} MB\n"
        f"**Status**: Encoding..."
    )
    try:
        await message.edit(progress_message)
    except FloodWait as e:
        print(f"FloodWait encountered: sleeping for {e.value} seconds.")
        await asyncio.sleep(e.value)  # Handle Telegram rate limit

# Video handler
@app.on_message(filters.video)
async def handle_video(client, message: Message):
    video = message.video
    input_file = await message.download()
    output_file = f"compressed_{video.file_name}"

    duration = video.duration
    original_size = os.path.getsize(input_file) / (1024 * 1024)
    progress_message = await message.reply_text("📥 Downloaded video. Starting compression...")

    try:
        await compress_video(
            input_file,
            output_file,
            duration,
            original_size,
            lambda percentage, current_size, estimated_size, start_time: progress_handler(
                progress_message, percentage, current_size, estimated_size, start_time
            ),
        )
        final_file_size = os.path.getsize(output_file) / (1024 * 1024)
        await progress_message.edit(f"✅ Compression complete! Final size: {final_file_size:.2f} MB. Uploading...")
        await message.reply_video(output_file, caption="Here is your compressed video 🎥")
    except Exception as e:
        await progress_message.edit(f"❌ Compression failed: {str(e)}")
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
