import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import ffmpeg
from time import time
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from config import API_ID, API_HASH, BOT_TOKEN


# Create a Pyrogram Client
app = Client("audio_compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Progress function for download and upload
async def progress(current, total, message, start_time):
    now = time()
    diff = now - start_time
    if diff > 0:
        percentage = current * 100 / total
        speed = current / diff
        time_to_completion = (total - current) / speed
        progress_str = "{0:.1f}%".format(percentage)
        speed_str = "{0:.2f} MB/s".format(speed / (1024 * 1024))
        time_str = "{0:.2f} seconds".format(time_to_completion)
        
        text = f"**Progress:** {progress_str}\n**Speed:** {speed_str}\n**ETA:** {time_str}"
        await message.edit(text)

# Function to compress audio using FFmpeg
async def compress_audio(input_file: str, output_file: str):
    try:
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', input_file, '-c:a', 'aac', '-b:a', '128k', '-y', output_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"FFmpeg error: {stderr.decode().strip()}")
            return False

        return True
    except Exception as e:
        print(f"Error during compression: {e}")
        return False

# Function to extract metadata
def extract_audio_metadata(file_loc: str):
    title = None
    artist = None
    duration = 0
    thumb = None

    metadata = extractMetadata(createParser(file_loc))
    if metadata:
        if metadata.has("title"):
            title = metadata.get("title")
        if metadata.has("artist"):
            artist = metadata.get("artist")
        if metadata.has("duration"):
            duration = metadata.get("duration").seconds

    return title, artist, duration, thumb

# Command handler for /compress_audio
@app.on_message(filters.command("compress_audio") & filters.reply)
async def compress_audio_command(client: Client, message: Message):
    # Check if the replied message has an audio or document file
    if message.reply_to_message.audio or message.reply_to_message.document:
        # Inform the user that the download is starting
        status_message = await message.reply_text("Downloading audio file...")
        
        # Download the file with progress
        start_time = time()
        file_path = await message.reply_to_message.download(
            progress=progress, progress_args=(status_message, "Downloading audio file", start_time)
        )
        
        # Extract metadata
        title, artist, duration, thumb = extract_audio_metadata(file_path)
        file_size = os.path.getsize(file_path)

        # Log metadata (optional)
        print(f"Title: {title}, Artist: {artist}, Duration: {duration} seconds, Size: {file_size} bytes")
        
        # Define the output file path
        output_file = f"compressed_{os.path.basename(file_path)}.aac"
        
        # Inform the user that compression is starting
        await status_message.edit("Compressing audio file...")
        
        # Compress the audio file
        compression_successful = await compress_audio(file_path, output_file)
        
        if not compression_successful or os.path.getsize(output_file) == 0:
            await status_message.edit("Compression failed. Please try again.")
            return

        # Inform the user that the upload is starting
        await status_message.edit("Uploading compressed audio file...")
        
        # Upload the compressed audio file with progress
        start_time = time()
        await message.reply_document(
            output_file, 
            caption=f"**Title:** {title}\n**Artist:** {artist}\n**Duration:** {duration} seconds\n**Size:** {file_size / (1024 * 1024):.2f} MB",
            progress=progress, 
            progress_args=(status_message, "uploading compressed audio file", start_time)
        )
        
        # Clean up temporary files
        os.remove(file_path)
        os.remove(output_file)
        
        # Inform the user that the process is complete
        await status_message.edit("Audio compression complete.")
    else:
        await message.reply_text("Please reply to an audio or document file to compress.")

# Run the bot
app.run()
