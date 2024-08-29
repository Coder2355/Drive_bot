import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import ffmpeg
from time import time
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from config import API_ID, API_HASH, BOT_TOKEN

# Create a Pyrogram Client
app = Client("audio_compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global variable to store file paths and format choices
downloaded_files = {}

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
async def compress_audio(input_file: str, output_file: str, codec: str, bitrate: str):
    try:
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', input_file, '-c:a', codec, '-b:a', bitrate, '-y', output_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"FFmpeg error: {stderr.decode().strip()}")
            return False

        return output_file  # Return the new output file path
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
            progress=progress, progress_args=(status_message, start_time)
        )
        
        # Store the downloaded file path associated with the message ID
        downloaded_files[message.id] = file_path

        # Ask the user for the output format using inline keyboard buttons
        buttons = [
            [InlineKeyboardButton("MP3", callback_data=f"compress_mp3_{message.id}")],
            [InlineKeyboardButton("AAC", callback_data=f"compress_aac_{message.id}")],
            [InlineKeyboardButton("Opus", callback_data=f"compress_opus_{message.id}")],
            [InlineKeyboardButton("OGG", callback_data=f"compress_ogg_{message.id}")],
            [InlineKeyboardButton("WAV", callback_data=f"compress_wav_{message.id}")],
            [InlineKeyboardButton("AC3", callback_data=f"compress_ac3_{message.id}")],
            [InlineKeyboardButton("Cancel", callback_data=f"compress_cancel_{message.id}")]
        ]

        await status_message.edit(
            "Please select the output format for compression:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await message.reply_text("Please reply to an audio or document file to compress.")

# Callback handler for format selection
@app.on_callback_query(filters.regex(r"compress_(.*?)_(\d+)"))
async def format_selection(client: Client, callback_query):
    data = callback_query.data.split("_")
    format_choice = data[1]
    message_id = int(data[2])

    # Retrieve the downloaded file path
    file_path = downloaded_files.get(message_id)
    
    if not file_path:
        await callback_query.message.edit("File not found. Please try again.")
        return

    if format_choice == "cancel":
        # Clean up and inform the user
        os.remove(file_path)
        del downloaded_files[message_id]
        await callback_query.message.edit("Compression cancelled.")
        return

    # Define codec and extension based on the format choice
    codec_map = {
        "mp3": ("libmp3lame", "128k", ".mp3"),
        "aac": ("aac", "34k", ".aac"),
        "opus": ("libopus", "34k", ".opus"),
        "ogg": ("libvorbis", "128k", ".ogg"),
        "wav": ("pcm_s16le", "128k", ".wav"),
        "ac3": ("ac3", "192k", ".ac3")
    }

    codec, bitrate, extension = codec_map.get(format_choice, (None, None, None))

    if codec is None:
        await callback_query.message.edit("Invalid format selected. Please try again.")
        return

    # Extract metadata
    title, artist, duration, thumb = extract_audio_metadata(file_path)
    file_size = os.path.getsize(file_path)

    # Define the output file path
    output_file = f"compressed_{os.path.basename(file_path)}{extension}"
    
    # Inform the user that compression is starting
    await callback_query.message.edit("Compressing audio file...")
    
    # Compress the audio file
    compressed_file = await compress_audio(file_path, output_file, codec, bitrate)
    
    if not compressed_file or os.path.getsize(compressed_file) == 0:
        await callback_query.message.edit("Compression failed. Please try again.")
        return

    # Inform the user that the upload is starting
    await callback_query.message.edit("Uploading compressed audio file...")
    
    # Upload the compressed audio file with progress
    start_time = time()
    await callback_query.message.reply_document(
        compressed_file, 
        caption=f"**Title:** {title}\n**Artist:** {artist}\n**Duration:** {duration} seconds\n**Size:** {file_size / (1024 * 1024):.2f} MB",
        progress=progress, 
        progress_args=(callback_query.message, start_time)
    )
    
    # Clean up temporary files
    os.remove(file_path)
    os.remove(compressed_file)
    del downloaded_files[message_id]

    # Inform the user that the process is complete
    await callback_query.message.edit("Audio compression complete.")

# Run the bot
app.run()
