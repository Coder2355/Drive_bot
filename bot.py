import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from time import time
from math import floor

from config import API_ID, API_HASH, BOT_TOKEN

# Create Pyrogram Client
app = Client("compress_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to calculate estimated output file size
def calculate_estimated_size(current_time, duration, bitrate):
    """Estimate the output file size dynamically during encoding."""
    if duration == 0 or current_time == 0:
        return 0
    return (bitrate / 8) * current_time / (1024 * 1024)

# Function to extract FFmpeg progress and report encoding status
async def compress_video(input_file, output_file, duration, bitrate, progress_callback):
    """Compress the video using FFmpeg and update progress dynamically."""
    start_time = time()
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", input_file,
        "-vf", "scale=-1:240",  # Scale to 240p
        "-c:v", "libx264",  # Use H.264 codec
        "-preset", "fast",  # Set compression speed
        "-crf", "28",  # Quality factor (lower is better, 23-28 recommended)
        "-c:a", "aac",  # Use AAC audio codec
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
                current_file_size = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0
                estimated_size = calculate_estimated_size(current_time, duration, bitrate)
                await progress_callback(percentage, current_file_size, estimated_size, start_time)

    await process.wait()

# Function to update progress with progress bar and file sizes
async def progress_handler(message, percentage, current_size, estimated_size, start_time):
    """Display the progress bar and dynamically update encoding status."""
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
    except:
        pass  # Handle cases where the message is edited/deleted simultaneously

# Handler for video messages
@app.on_message(filters.video)
async def handle_video(client, message: Message):
    """Handle incoming video messages and start compression."""
    video = message.video
    input_file = await message.download()
    output_file = f"compressed_{video.file_name}"

    duration = video.duration  # Video duration in seconds
    bitrate = 500_000  # Approximate bitrate for 240p video in bits per second
    progress_message = await message.reply_text("📥 Downloaded video. Starting compression...")

    try:
        await compress_video(
            input_file,
            output_file,
            duration,
            bitrate,
            lambda percentage, current_size, estimated_size, start_time: progress_handler(
                progress_message, percentage, current_size, estimated_size, start_time
            ),
        )
        final_file_size = os.path.getsize(output_file) / (1024 * 1024)  # Final file size in MB
        await progress_message.edit(f"✅ Compression complete! Final size: {final_file_size:.2f} MB. Uploading...")
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
