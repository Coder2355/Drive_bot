import os
import re
import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("video_compress_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary directory for storing files
DOWNLOAD_DIR = "downloads"

# Inline keyboard for compress confirmation
COMPRESS_BUTTONS = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Compress to 480p", callback_data="compress_480p")]]
)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "Hi! I am a video compression bot.\n\n"
        "Send me a video file, and I'll compress it to 480p for you.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Help", callback_data="help")]])
    )

@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    file = message.video or message.document
    if not file.file_name.lower().endswith((".mp4", ".mkv", ".mov")):
        await message.reply_text("Please send a valid video file (MP4, MKV, MOV).")
        return

    await message.reply_text(
        "Do you want to compress this video to 480p?",
        reply_markup=COMPRESS_BUTTONS
    )

@app.on_callback_query(filters.regex("compress_480p"))
async def compress_video(client, callback_query):
    message = callback_query.message
    await callback_query.answer()
    await message.edit_text("Downloading video...")

    # Download video
    video = message.reply_to_message.video or message.reply_to_message.document
    file_path = await client.download_media(video, file_name=f"{DOWNLOAD_DIR}/{video.file_name}")

    compressed_path = f"{DOWNLOAD_DIR}/compressed_{video.file_name}"
    start_time = time()

    try:
        await message.edit_text("Compressing video to 480p...")

        # Command for FFmpeg
        command = [
            "ffmpeg", "-i", file_path, "-vf", "scale=854:480", "-c:v", "libx264",
            "-preset", "slow", "-crf", "28", "-c:a", "aac", "-b:a", "128k", compressed_path
        ]

        process = await asyncio.create_subprocess_exec(
            *command, stderr=asyncio.subprocess.PIPE
        )

        # Parse FFmpeg progress
        total_duration = await get_video_duration(file_path)
        async for line in process.stderr:
            line = line.decode("utf-8")
            if "frame=" in line:
                progress = parse_ffmpeg_progress(line, total_duration, compressed_path)
                if progress:
                    await message.edit_text(progress)

        await process.wait()

        if not os.path.exists(compressed_path):
            await message.edit_text("Failed to compress the video.")
            return

        end_time = time()
        await message.edit_text(
            f"Compression completed in {int(end_time - start_time)} seconds. Uploading..."
        )

        await client.send_video(
            chat_id=message.chat.id,
            video=compressed_path,
            caption="Here is your compressed video in 480p!"
        )
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
    finally:
        # Clean up temporary files
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(compressed_path):
            os.remove(compressed_path)

@app.on_callback_query(filters.regex("help"))
async def help_command(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "Send me a video file, and I'll compress it to 480p resolution.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "Send a video to compress."
    )

async def get_video_duration(file_path):
    """Extract the total duration of the video using FFmpeg."""
    command = [
        "ffprobe", "-i", file_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"
    ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    return float(stdout.strip())

def parse_ffmpeg_progress(line, total_duration, output_path):
    """Parse FFmpeg progress and generate a progress message."""
    frame_regex = r"frame=\s*(\d+)"
    time_regex = r"time=(\d+:\d+:\d+\.\d+)"
    speed_regex = r"speed=\s*([\d\.x]+)"

    frame_match = re.search(frame_regex, line)
    time_match = re.search(time_regex, line)
    speed_match = re.search(speed_regex, line)

    if time_match:
        # Convert "hh:mm:ss.ms" to seconds
        time_parts = time_match.group(1).split(":")
        elapsed_time = (
            int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + float(time_parts[2])
        )
        progress_percent = (elapsed_time / total_duration) * 100

        # Get file size if available
        output_size = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0

        message = (
            f"**Encoding Progress**\n\n"
            f"**Progress:** {progress_percent:.2f}%\n"
            f"**Elapsed Time:** {elapsed_time:.2f}s\n"
            f"**Speed:** {speed_match.group(1) if speed_match else 'N/A'}\n"
            f"**Output Size:** {output_size:.2f} MB"
        )
        return message
    return None

if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    app.run()
