import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import ffmpeg
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIR

# Initialize the bot with your API credentials
app = Client("audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Dictionary to store user status for audio merging
merger = {}

# Store the first audio file's message details
audio_storage = {}

@app.on_message(filters.audio | filters.document)
async def audio_handler(client: Client, message: Message):
    # Create the inline keyboard with the audio+audio button
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("audio+audio", callback_data="merge_audio")]]
    )
    await message.reply_text("Select an option:", reply_markup=keyboard)

@app.on_callback_query(filters.regex("merge_audio"))
async def on_audio_plus_audio_button(client: Client, callback_query):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    # Check if the message is a reply to another message with audio or document
    if callback_query.message.reply_to_message and (callback_query.message.reply_to_message.audio or callback_query.message.reply_to_message.document):
        # Store the user ID in the merger dictionary
        merger[chat_id] = user_id

        # Send downloading message
        downloading_message = await callback_query.message.reply_text("Downloading the first audio... 🎵")

        # Download the first audio
        audio_id = callback_query.message.reply_to_message.id
        first_audio_path = await client.download_media(
            callback_query.message.reply_to_message,
            file_name=os.path.join(DOWNLOAD_DIR, f"audio1_{audio_id}.mp3"),
            progress=progress_bar,
            progress_args=("Downloading first audio 🎵", callback_query.message)
        )

        # Store the path of the first audio
        audio_storage[chat_id] = {
            "first_audio": first_audio_path,
            "user_id": user_id
        }

        # Notify that the first audio has been downloaded
        await downloading_message.edit_text("First audio downloaded. Please send the second audio file.")
    else:
        await callback_query.message.reply_text("Please reply to an audio file or document with the audio+audio button.")
        
@app.on_message(filters.audio | filters.document)
async def process_audio(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if user is in the merger dictionary
    if chat_id in merger and merger[chat_id] == user_id:
        if message.audio or message.document:
            # Send downloading message
            downloading_message = await message.reply_text("Downloading the second audio... 🎵")

            # Download the second audio
            audio_id = message.id
            second_audio_path = await client.download_media(
                message,
                file_name=os.path.join(DOWNLOAD_DIR, f"audio2_{audio_id}.mp3"),
                progress=progress_bar,
                progress_args=("Downloading second audio 🎵", message)
            )

            # Notify that the second audio has been downloaded
            await downloading_message.edit_text("Second audio downloaded. Merging the audios... 🎵")

            first_audio_path = audio_storage[chat_id]["first_audio"]

            # Merge the two audio files using FFmpeg
            merged_audio_path = os.path.join(DOWNLOAD_DIR, f"merged_{chat_id}.mp3")
            (
                ffmpeg
                .concat(ffmpeg.input(first_audio_path), ffmpeg.input(second_audio_path), v=0, a=1)
                .output(merged_audio_path)
                .run(overwrite_output=True)
            )

            # Extract metadata
            title, artist, duration, thumb = extract_audio_metadata(merged_audio_path)

            # Send uploading message
            uploading_message = await message.reply_text("Uploading the merged audio... 🎵")

            # Send the merged audio file with metadata
            await client.send_audio(
                chat_id=chat_id,
                audio=merged_audio_path,
                caption=f"Here's your merged audio! 🎵\n\nTitle: {title}\nArtist: {artist}\nDuration: {duration} seconds",
                thumb=thumb,
                title=title,
                performer=artist,
                duration=duration
            )

            # Notify that the upload is complete
            await uploading_message.delete()

            # Clean up
            os.remove(first_audio_path)
            os.remove(second_audio_path)
            os.remove(merged_audio_path)
            del audio_storage[chat_id]
            del merger[chat_id]
        else:
            await message.reply_text("Please send a valid audio file or document.")
    else:
        # If the user is not in the merger dictionary, process normally or start a new merge
        await message.reply_text("No merge process is active. Please start a new one with the audio+audio button.")

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text("Hello! Send an audio file or document, then click the audio+audio button to start the merging process.")

# Progress bar function
async def progress_bar(current, total, message, description):
    progress = f"{description}\n[{current * 100 / total:.1f}%]"
    await message.edit_text(progress)

# Function to extract audio metadata
def extract_audio_metadata(file_loc):
    title = None
    artist = None
    thumb = None
    duration = 0

    metadata = extractMetadata(createParser(file_loc))
    if metadata:
        if metadata.has("title"):
            title = metadata.get("title")
        if metadata.has("artist"):
            artist = metadata.get("artist")
        if metadata.has("duration"):
            duration = metadata.get("duration").seconds

    return title, artist, duration, thumb

app.run()
