import os
import uuid
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

user_state = {}

async def merge_video_audio(video_path, audio_path, output_path):
    try:
        input_video = ffmpeg.input(video_path)
        input_audio = ffmpeg.input(audio_path)
        ffmpeg.concat(input_video, input_audio, v=1, a=1).output(output_path).run(overwrite_output=True)
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e}")

async def start(client: Client, message: Message):
    await message.reply_text("Hello! I can help you merge video and audio files. Use the /merge command to start.")

async def merge_command(client: Client, message: Message):
    user_state[message.chat.id] = {"state": "awaiting_video"}
    await message.reply_text("Please send the video file as either a video or document.")

async def receive_video(client: Client, message: Message):
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("state") == "awaiting_video":
        file_name = message.video.file_name if message.video else message.document.file_name
        file_extension = os.path.splitext(file_name)[1].lower()
        if file_extension in ['.mp4', '.mkv', '.avi', '.mov']:
            unique_id = str(uuid.uuid4())
            video_path = await message.download(f"{config.DOWNLOAD_DIR}/video_{unique_id}{file_extension}")
            user_state[chat_id]["video"] = video_path
            user_state[chat_id]["state"] = "awaiting_audio"
            await message.reply_text("Video received! Now, please send the audio file.")
        else:
            await message.reply_text("Please send a valid video file.")

async def receive_audio(client: Client, message: Message):
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("state") == "awaiting_audio":
        unique_id = str(uuid.uuid4())
        audio_path = await message.download(f"{config.DOWNLOAD_DIR}/audio_{unique_id}.mp3")
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
