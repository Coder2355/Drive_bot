import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIR

# Initialize the bot with your API credentials
app = Client("audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Store the first audio file's message details
audio_storage = {}

# Store users who have clicked the audio+audio button
merger = {}

@app.on_message(filters.audio | filters.document)
async def handle_audio(client: Client, message: Message):
    # Check if the user is in the merger dictionary
    if message.from_user.id in merger:
        # Start merging process
        await process_second_audio(client, message)
    else:
        # Display the inline button for audio+audio
        await message.reply_text(
            "Click the button to merge this audio with another one.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("audio+audio", callback_data="merge_audio")]
            ])
        )

@app.on_callback_query(filters.regex("merge_audio"))
async def on_merge_audio_click(client: Client, callback_query):
    user_id = callback_query.from_user.id

    # Store the user_id in the merger dictionary
    merger[user_id] = True

    # Acknowledge the button click
    await callback_query.answer("Now send the second audio file to merge with this one.")

    # Store the first audio file
    audio_id = callback_query.message.id
    first_audio_path = await client.download_media(
        callback_query.message,
        file_name=os.path.join(DOWNLOAD_DIR, f"audio1_{audio_id}.mp3"),
        progress=progress_bar,
        progress_args=("Downloading first audio 🎵", callback_query.message)
    )

    # Store the path of the first audio and the user_id
    audio_storage[user_id] = {
        "first_audio": first_audio_path,
        "user_id": user_id
    }

@app.on_message(filters.audio | filters.document)
async def process_second_audio(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in merger and user_id in audio_storage:
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

            first_audio_path = audio_storage[user_id]["first_audio"]

            # Merge the two audio files using FFmpeg
            merged_audio_path = os.path.join(DOWNLOAD_DIR, f"merged_{user_id}.mp3")
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
                chat_id=message.chat.id,
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
            del audio_storage[user_id]
            del merger[user_id]  # Remove the user from the merger dictionary
        else:
            await message.reply_text("Please send a valid audio file or document.")
    else:
        await message.reply_text("No merge process is active. Please start a new one.")

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text("Hello! Send an audio file to start the merging process or use the audio+audio button to merge two audio files.")

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
