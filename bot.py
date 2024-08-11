import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import ffmpeg
from aiohttp import web
from config import config

app = Client(
    "media_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Ensure the download directory exists
if not os.path.exists(config.DOWNLOAD_DIR):
    os.makedirs(config.DOWNLOAD_DIR)

# State to keep track of what the user is doing
user_state = {}

async def merge_video_audio(video_path, audio_path, output_path):
    input_video = ffmpeg.input(video_path)
    input_audio = ffmpeg.input(audio_path)
    ffmpeg.concat(input_video, input_audio, v=1, a=1).output(output_path).run(overwrite_output=True)

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text("Hello! I can help you merge video and audio files. Use the /merge command to start.")

@app.on_message(filters.command("merge"))
async def merge_command(client: Client, message: Message):
    user_state[message.chat.id] = {"state": "awaiting_video"}
    await message.reply_text("Please send the video file as either a video or document.")

@app.on_message((filters.video | filters.document) & filters.private)
async def receive_video(client: Client, message: Message):
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("state") == "awaiting_video":
        # Check if the file is a video or document
        file_name = message.video.file_name if message.video else message.document.file_name
        file_extension = os.path.splitext(file_name)[1].lower()
        if file_extension in ['.mp4', '.mkv', '.avi', '.mov']:
            user_state[chat_id]["video"] = await message.download(config.DOWNLOAD_DIR)
            user_state[chat_id]["state"] = "awaiting_audio"
            await message.reply_text("Video received! Now, please send the audio file.")
        else:
            await message.reply_text("Please send a valid video file.")

@app.on_message(filters.audio & filters.private)
async def receive_audio(client: Client, message: Message):
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("state") == "awaiting_audio":
        audio_path = await message.download(config.DOWNLOAD_DIR)
        video_path = user_state[chat_id]["video"]
        output_path = os.path.join(config.DOWNLOAD_DIR, f"merged_{message.chat.id}.mp4")

        await message.reply_text("Merging video and audio...")

        await merge_video_audio(video_path, audio_path, output_path)

        await client.send_video(chat_id, output_path)

        # Clean up
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)
        user_state.pop(chat_id, None)
        await message.reply_text("Here is your merged video!")


if __name__ == "__main__":
    app.run()
