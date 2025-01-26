import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from time import time

from config import API_ID, API_HASH, BOT_TOKEN


# Create Pyrogram Client
app = Client("compress_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to extract FFmpeg progress and report encoding status
async def compress_video(input_file, output_file, duration, progress_callback):
    start_time = time()
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", input_file,
        "-vf", "scale=-1:480",  # Scale to 480p
        "-c:v", "libx264",  # Use H.264 codec
        "-preset", "fast",  # Set compression speed
        "-crf", "28",  # Quality factor (lower is better, 23-28 recommended)
        "-c:a", "aac",  # Use AAC audio codec
        "-b:a", "128k",  # Audio bitrate
        "-progress", "pipe:1",  # Output progress to pipe
        "-y",  # Overwrite output
        output_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
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
                percentage = (current_time / duration) * 100
                await progress_callback(percentage, start_time)
    
    await process.wait()

# Function to update progress
async def progress_handler(message, percentage, start_time):
    elapsed_time = time() - start_time
    progress_message = (
        f"🎥 **Encoding Progress**:\n"
        f"**Percentage**: {percentage:.2f}%\n"
        f"**Elapsed Time**: {elapsed_time:.2f} seconds\n"
        f"**Status**: Encoding..."
    )
    try:
        await message.edit(progress_message)
    except:
        pass  # Prevent errors if the message is edited/deleted simultaneously

# Handler for video messages
@app.on_message(filters.video)  # Removed ~filters.edited
async def handle_video(client, message: Message):
    video = message.video
    input_file = await message.download()
    output_file = f"compressed_{video.file_name}"

    duration = video.duration  # Video duration in seconds
    progress_message = await message.reply_text("📥 Downloaded video. Starting compression...")

    try:
        await compress_video(
            input_file,
            output_file,
            duration,
            lambda percentage, start_time: progress_handler(progress_message, percentage, start_time)
        )
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # File size in MB
        await progress_message.edit(f"✅ Compression complete! Compressed size: {file_size:.2f} MB. Uploading...")
        await message.reply_video(output_file, caption="Here is your compressed video 🎥")
    except Exception as e:
        await progress_message.edit(f"❌ Compression failed: {str(e)}")
    finally:
        # Clean up files
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
