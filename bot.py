from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import ffmpeg
import asyncio
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize the bot
app = Client("audio_converter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store user data
user_data = {}

# Inline keyboard buttons for audio formats
audio_formats = InlineKeyboardMarkup([
    [InlineKeyboardButton("AC3", callback_data="ac3"), InlineKeyboardButton("MP3", callback_data="mp3")],
    [InlineKeyboardButton("WAV", callback_data="wav"), InlineKeyboardButton("FLAC", callback_data="flac")],
    [InlineKeyboardButton("OGG", callback_data="ogg"), InlineKeyboardButton("OPUS", callback_data="opus")],
    [InlineKeyboardButton("AAC", callback_data="aac"), InlineKeyboardButton("M4A", callback_data="m4a")],
    [InlineKeyboardButton("AIFF", callback_data="aiff"), InlineKeyboardButton("WMA", callback_data="wma")],
    [InlineKeyboardButton("CANCEL", callback_data="cancel")]
])

# Progress callback function
async def progress(current, total, message, action):
    percent_complete = current * 100 / total
    await message.edit_text(f"{action}: {percent_complete:.1f}%")

# Function to extract metadata
def extract_audio_metadata(file_loc):
    title = None
    artist = None
    duration = 0
    size = os.path.getsize(file_loc)
    format = os.path.splitext(file_loc)[1].lstrip('.').upper()

    metadata = extractMetadata(createParser(file_loc))
    if metadata:
        if metadata.has("title"):
            title = metadata.get("title")
        if metadata.has("artist"):
            artist = metadata.get("artist")
        if metadata.has("duration"):
            duration = metadata.get("duration").seconds

    return title, artist, duration, size, format

# Handle the /start command
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "Welcome to the Audio Converter Bot! 🛠️\n\n"
        "To convert an audio file, reply to it with the /convert_audio command.\n"
        "You can then select the format you want to convert it to using the inline keyboard.",
        quote=True
    )

# Handle the /convert_audio command
@app.on_message(filters.command("convert_audio") & filters.reply)
async def convert_audio(client, message):
    if not (message.reply_to_message.audio or message.reply_to_message.document):
        await message.reply_text("Please reply to an audio file or document with the /convert_audio command.")
        return

    # Download the audio file with progress
    download_message = await message.reply_text("Downloading...")
    file = await message.reply_to_message.download(progress=progress, progress_args=(download_message, "Downloading"))

    # Extract metadata
    title, artist, duration, size, file_format = extract_audio_metadata(file)
    
    metadata_info = f"Title: {title or 'Unknown'}\nArtist: {artist or 'Unknown'}\nDuration: {duration // 60}:{duration % 60:02d}\nSize: {size / (1024 * 1024):.2f} MB\nFormat: {file_format}"
    await download_message.edit_text(
        f"{metadata_info}\n\nPlease choose the format you want to convert to:", 
        reply_markup=audio_formats
    )

    # Store the file path in the user_data dictionary
    user_data[message.from_user.id] = {'file_path': file}

# Handle the callback queries from the inline keyboard
@app.on_callback_query()
async def handle_callback(client, callback_query):
    user_id = callback_query.from_user.id
    file_path = user_data.get(user_id, {}).get('file_path')
    
    if not file_path:
        await callback_query.message.edit_text("Error: No file found. Please reply to an audio file first.")
        return

    format_selected = callback_query.data

    # Check if the file is already in the desired format
    _, _, _, _, current_format = extract_audio_metadata(file_path)
    if current_format.upper() == format_selected.upper():
        await callback_query.message.edit_text("The audio file is already in the desired format.")
        return

    new_file_path = f"{os.path.splitext(file_path)[0]}.{format_selected}"

    try:
        await callback_query.message.edit_text(f"Converting to {format_selected.upper()}...")
        
        # Convert the audio using FFmpeg
        await asyncio.to_thread(ffmpeg.input(file_path).output(new_file_path).run)

        upload_message = await callback_query.message.edit_text("Uploading...")
        await client.document(
            chat_id=callback_query.message.chat.id,
            document=new_file_path,
            caption=f"Here is your file converted to {format_selected.upper()}",
            progress=progress,
            progress_args=(upload_message, "Uploading")
        )
        
        os.remove(file_path)
        os.remove(new_file_path)

    except Exception as e:
        await callback_query.message.edit_text(f"Error during conversion: {str(e)}")
        os.remove(file_path)
        user_data.pop(user_id, None)  # Remove user data

if __name__ == "__main__":
    app.run()
