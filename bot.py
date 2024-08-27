import os
import asyncio
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config

# Configure your bot
API_ID = Config.API_ID
API_HASH = Config.API_HASH
BOT_TOKEN = Config.BOT_TOKEN

# Create the bot client
app = Client("audio_video_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global variables to store the files temporarily
merge_audio_files = {}

# Start command handler
@app.on_message(filters.command("start"))
async def start_message(client: Client, message: Message):
    start_text = (
        "👋 Hello! I'm the Audio+Video Merger Bot.\n\n"
        "I can help you merge audio files together or merge an audio file with a video.\n\n"
        "**Commands**:\n"
        "🎵 `/merge_audio` - Reply to an audio file to start the audio merging process.\n"
        "🎥 `/merge_video` - Reply to a video file to start the video + audio merging process.\n\n"
        "Just send me the files, and I'll take care of the rest!"
    )
    await message.reply_text(start_text)

# /merge_audio command handler
@app.on_message(filters.command("merge_audio") & filters.reply & (filters.audio | filters.document))
async def merge_audio_command(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in merge_audio_files:
        await message.reply_text("You already have a pending merge process. Please finish it first.")
        return

    if not message.reply_to_message or not (message.reply_to_message.audio or message.reply_to_message.document):
        await message.reply_text("Please reply to the first audio file with the /merge_audio command.")
        return

    # Notify the user that downloading is starting
    download_msg = await message.reply_text("Downloading the first audio file...")

    # Download the first audio file
    audio_file_path = await message.reply_to_message.download()

    # Store the file path for merging
    merge_audio_files[user_id] = {
        "first_audio": audio_file_path,
        "second_audio": None,
        "output": f"merged_audio_{user_id}.mp3"
    }

    # Update the user and remove the download message
    await download_msg.delete()
    await message.reply_text("First audio file downloaded. Now, send the second audio file to merge.")

# Handle the second audio file
@app.on_message((filters.audio | filters.document) & filters.user(lambda _, __, m: m.from_user.id in merge_audio_files))
async def second_audio_handler(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in merge_audio_files:
        return

    if merge_audio_files[user_id]["second_audio"]:
        await message.reply_text("You have already sent the second audio file. Please wait while I merge the files.")
        return

    # Notify the user that downloading is starting
    download_msg = await message.reply_text("Downloading the second audio file...")

    # Download the second audio file
    second_audio_path = await message.download()

    # Update the second audio file path in the dictionary
    merge_audio_files[user_id]["second_audio"] = second_audio_path

    # Update the user and remove the download message
    await download_msg.delete()
    await message.reply_text("Second audio file downloaded. Merging the audio files...")

    # Paths
    first_audio = merge_audio_files[user_id]["first_audio"]
    second_audio = merge_audio_files[user_id]["second_audio"]
    output_file = merge_audio_files[user_id]["output"]

    # Merge audio files using FFmpeg
    await merge_audio_files_ffmpeg(first_audio, second_audio, output_file)

    # Notify the user that uploading is starting
    upload_msg = await message.reply_text("Uploading the merged audio file...")

    # Send the merged audio
    await message.reply_audio(audio=output_file)

    # Clean up and delete the upload message
    await upload_msg.delete()

    # Clean up
    os.remove(first_audio)
    os.remove(second_audio)
    os.remove(output_file)

    # Clear the stored data
    merge_audio_files.pop(user_id)

async def merge_audio_files_ffmpeg(first_audio, second_audio, output):
    # Merge audio files using FFmpeg
    await asyncio.to_thread(
        ffmpeg.input(first_audio).input(second_audio).filter_complex('amix=inputs=2:duration=first:dropout_transition=2').output(output).run, overwrite_output=True
    )

if __name__ == "__main__":
    app.run()
