from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import asyncio
import subprocess
import time
from config import API_ID, API_HASH, BOT_TOKEN

# Bot Configuration
bot = Client(
    "video_compress_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Temporary paths
DOWNLOAD_PATH = "./downloads/"
COMPRESSED_PATH = "./compressed/"

# Ensuring directories exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(COMPRESSED_PATH, exist_ok=True)

@bot.on_message(filters.video | filters.document)
async def handle_video(client, message):
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Compress to 480p", callback_data="compress_480p")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ])
    await message.reply_text(
        "Choose an action for this video:",
        reply_markup=reply_markup
    )

@bot.on_callback_query()
async def handle_callback(client, callback_query):
    if callback_query.data == "cancel":
        await callback_query.message.edit_text("Operation canceled.")
        return

    if callback_query.data == "compress_480p":
        await callback_query.message.edit_text("Starting compression to 480p...")
        message = callback_query.message.reply_to_message

        # Download the video
        file_path = await download_video(client, message)
        if not file_path:
            await callback_query.message.edit_text("Failed to download the video.")
            return

        # Compress the video to 480p
        compressed_path = os.path.join(COMPRESSED_PATH, f"compressed_{os.path.basename(file_path)}")
        start_time = time.time()
        compression_success = await compress_video(file_path, compressed_path, callback_query.message, start_time)

        if compression_success:
            # Upload the compressed video
            await callback_query.message.edit_text("Uploading compressed video...")
            await client.send_video(
                chat_id=message.chat.id,
                video=compressed_path,
                caption="Here is your compressed video (480p)."
            )
            await callback_query.message.delete()
        else:
            await callback_query.message.edit_text("Compression failed.")

        # Clean up
        os.remove(file_path)
        if os.path.exists(compressed_path):
            os.remove(compressed_path)

async def download_video(client, message):
    try:
        file_path = await client.download_media(message, file_name=DOWNLOAD_PATH)
        return file_path
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

async def compress_video(input_path, output_path, status_message, start_time):
    try:
        command = [
            "ffmpeg", "-i", input_path,
            "-vf", "scale=-1:480",
            "-preset", "slow",
            "-crf", "28",  # Lower CRF means better quality
            output_path
        ]
        
        # Run FFmpeg and capture progress
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        total_size = os.path.getsize(input_path)
        while True:
            line = await process.stderr.readline()
            if not line:
                break

            line = line.decode("utf-8").strip()
            if "frame=" in line:
                progress = parse_ffmpeg_progress(line)
                elapsed_time = time.time() - start_time
                if progress:
                    percentage = (progress['frame'] / total_size) * 100
                    await status_message.edit_text(
                        f"**Encoding in Progress:**\n"
                        f"**Progress:** {percentage:.2f}%\n"
                        f"**Output Size:** {progress['size']} MB\n"
                        f"**Speed:** {progress['speed']}\n"
                        f"**Elapsed Time:** {elapsed_time:.2f} seconds\n"
                    )

        await process.wait()
        return process.returncode == 0
    except Exception as e:
        print(f"Error during compression: {e}")
        return False

def parse_ffmpeg_progress(line):
    """
    Parse FFmpeg progress output and extract relevant data.
    """
    try:
        data = {}
        if "size=" in line:
            parts = line.split(" ")
            for part in parts:
                if "=" in part:
                    key, value = part.split("=")
                    data[key] = value

            # Convert size to MB
            size_kb = int(data.get("size", "0").replace("kB", "").strip())
            data['size'] = round(size_kb / 1024, 2)  # Convert to MB

            return data
    except Exception as e:
        print(f"Error parsing progress: {e}")
        return None

if __name__ == "__main__":
    bot.run()
