import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("video_compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary download folder
DOWNLOAD_PATH = "downloads"

# Ensure the download directory exists
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# Start message
START_MESSAGE = "Hello! I am a video compressor bot. Send me a video, and I will compress it to 720p quality."

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        START_MESSAGE,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Source Code", url="https://github.com/your-repo")],
        ])
    )

@app.on_message(filters.video & filters.private)
async def compress_video(client, message):
    msg = await message.reply_text("Downloading your video...")
    video_path = await message.download(DOWNLOAD_PATH)
    compressed_video_path = os.path.join(DOWNLOAD_PATH, f"compressed_{message.video.file_name}")

    try:
        # Notify user about compression start
        await msg.edit_text("Compressing your video to 720p...")

        # Start compression with real-time progress tracking
        await encode_video(video_path, compressed_video_path, msg)

        # Notify user of upload progress
        compressed_size = os.path.getsize(compressed_video_path) / (1024 * 1024)  # In MB
        await msg.edit_text(f"Uploading the compressed video... (Size: {compressed_size:.2f} MB)")
        await message.reply_video(
            compressed_video_path,
            caption=f"Here is your compressed video in 720p quality.\n\n**Compressed Size:** {compressed_size:.2f} MB"
        )
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
    finally:
        # Clean up downloaded and processed files
        os.remove(video_path)
        if os.path.exists(compressed_video_path):
            os.remove(compressed_video_path)
        await msg.delete()

async def encode_video(input_path, output_path, progress_msg):
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", "scale=-1:240",  # Rescale video to 720p
        "-c:v", "libx264", "-preset", "slow", "-crf", "28",
        "-c:a", "aac", "-b:a", "38k", "-movflags", "+faststart",
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command, stderr=asyncio.subprocess.PIPE
    )
    
    total_duration = await get_video_duration(input_path)
    start_time = asyncio.get_event_loop().time()

    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        line = line.decode()
        if "time=" in line:
            # Parse encoding progress
            time_match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
            speed_match = re.search(r"speed=([\d.]+)x", line)
            
            if time_match:
                elapsed_time = time_match.group(1)
                progress = await calculate_progress(elapsed_time, total_duration)
                current_size = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0
                speed = speed_match.group(1) if speed_match else "N/A"
                elapsed = asyncio.get_event_loop().time() - start_time

                # Update progress bar
                await progress_msg.edit_text(
                    f"**Encoding Progress:** {progress:.2f}%\n"
                    f"**Output Size:** {current_size:.2f} MB\n"
                    f"**Elapsed Time:** {elapsed:.2f} seconds\n"
                    f"**Speed:** {speed}x\n"
                )

    await process.wait()
    if process.returncode != 0:
        raise Exception("Encoding failed")

async def get_video_duration(video_path):
    """Get video duration in seconds."""
    command = [
        "ffprobe", "-i", video_path, "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    return float(stdout.decode().strip())

async def calculate_progress(elapsed_time, total_duration):
    """Calculate encoding progress percentage."""
    h, m, s = map(float, elapsed_time.split(":"))
    elapsed_seconds = h * 3600 + m * 60 + s
    return (elapsed_seconds / total_duration) * 100

if __name__ == "__main__":
    app.run()
