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
merge_video_file = {}

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
@app.on_message(filters.command("merge_audio") & (filters.audio | filters.document))
async def merge_audio_command(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in merge_audio_files:
        await message.reply_text("You already have a pending merge process. Please finish it first.")
        return

    if not message.reply_to_message:
        await message.reply_text("Please reply to the first audio file with the /merge_audio command.")
        return

    # Download the first audio file
    audio_file_path = await message.reply_to_message.download()

    # Store the file path for merging
    merge_audio_files[user_id] = {
        "first_audio": audio_file_path,
        "second_audio": None,
        "output": f"merged_audio_{user_id}.mp3"
    }

    await message.reply_text("First audio file downloaded. Now, send the second audio file to merge.")

# Handle the second audio file
@app.on_message((filters.audio | filters.document) & filters.user(merge_audio_files.keys()))
async def second_audio_handler(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in merge_audio_files:
        return

    # Download the second audio file
    second_audio_path = await message.download()

    # Update the second audio file path in the dictionary
    merge_audio_files[user_id]["second_audio"] = second_audio_path

    # Paths
    first_audio = merge_audio_files[user_id]["first_audio"]
    second_audio = merge_audio_files[user_id]["second_audio"]
    output_file = merge_audio_files[user_id]["output"]

    # Merge audio files using FFmpeg
    await merge_audio_files_ffmpeg(first_audio, second_audio, output_file)

    # Send the merged audio
    await message.reply_audio(audio=output_file)

    # Clean up
    os.remove(first_audio)
    os.remove(second_audio)
    os.remove(output_file)

    # Clear the stored data
    merge_audio_files.pop(user_id)

async def merge_audio_files_ffmpeg(first_audio, second_audio, output):
    ffmpeg.input(first_audio).output(output).run(overwrite_output=True)
    ffmpeg.input(second_audio).output(output, filter_complex='[0][1]amix=inputs=2:duration=first:dropout_transition=2').run(overwrite_output=True)

# /merge_video command handler
@app.on_message(filters.command("merge_video") & (filters.video | filters.document))
async def merge_video_command(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in merge_video_file:
        await message.reply_text("You already have a pending merge process. Please finish it first.")
        return

    if not message.reply_to_message:
        await message.reply_text("Please reply to the video file with the /merge_video command.")
        return

    # Download the video file
    video_file_path = await message.reply_to_message.download()

    # Store the file path for merging
    merge_video_file[user_id] = {
        "video": video_file_path,
        "audio": None,
        "output": f"merged_video_{user_id}.mp4"
    }

    await message.reply_text("Video file downloaded. Now, send the audio file to merge.")

# Handle the audio file for video+audio merging
@app.on_message(filters.audio & filters.user(merge_video_file.keys()))
async def video_audio_handler(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in merge_video_file:
        return

    # Download the audio file
    audio_file_path = await message.download()

    # Update the audio file path in the dictionary
    merge_video_file[user_id]["audio"] = audio_file_path

    # Paths
    video_file = merge_video_file[user_id]["video"]
    output_file = merge_video_file[user_id]["output"]

    # Remove existing audio and merge with new audio
    await merge_video_audio_ffmpeg(video_file, audio_file_path, output_file)

    # Send the merged video
    await message.reply_video(video=output_file)

    # Clean up
    os.remove(video_file)
    os.remove(audio_file_path)
    os.remove(output_file)

    # Clear the stored data
    merge_video_file.pop(user_id)

async def merge_video_audio_ffmpeg(video, audio, output):
    ffmpeg.input(video).output(output, vn=True).run(overwrite_output=True)  # Remove audio
    ffmpeg.input(video).input(audio).output(output, vcodec='copy', acodec='aac').run(overwrite_output=True)  # Merge with new audio

if __name__ == "__main__":
    app.run()
