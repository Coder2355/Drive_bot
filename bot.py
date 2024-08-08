import os
import ffmpeg
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import config

load_dotenv()

# Initialize the bot with your API credentials
app = Client(
    "my_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Initialize Flask
api = Flask(__name__)

# Function to synchronize audio and video
async def synchronize_audio_video(video_path, audio_path, output_path):
    try:
        input_video = ffmpeg.input(video_path)
        input_audio = ffmpeg.input(audio_path)
        (
            ffmpeg
            .concat(input_video, input_audio, v=1, a=1)
            .output(output_path)
            .run()
        )
        return True
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e}")
        return False
    except Exception as e:
        print(f"General error: {e}")
        return False

@app.on_message(filters.command(["start"]))
async def start(client: Client, message: Message):
    await message.reply_text("Hello! Send me a video and an audio file to synchronize.")

@app.on_message(filters.video)
async def video_handler(client: Client, message: Message):
    video = message.video
    video_path = f"{video.file_id}.mp4"
    
    try:
        await client.download_media(video, video_path)
        await message.reply_text("Video received! Now send the audio file.")
    except Exception as e:
        await message.reply_text(f"Failed to download video: {e}")

@app.on_message(filters.audio)
async def audio_handler(client: Client, message: Message):
    audio = message.audio
    audio_path = f"{audio.file_id}.mp3"
    video_message = await client.get_messages(message.chat.id, message.reply_to_message_id)
    video_path = f"{video_message.video.file_id}.mp4"
    output_path = f"synchronized_{audio.file_id}.mp4"
    
    try:
        await client.download_media(audio, audio_path)
    except Exception as e:
        await message.reply_text(f"Failed to download audio: {e}")
        return

    await message.reply_text("Audio received! Synchronizing now...")
    
    if not os.path.exists(video_path):
        await message.reply_text("Video file not found. Make sure to send the video first.")
        os.remove(audio_path)
        return

    try:
        if await asyncio.to_thread(synchronize_audio_video, video_path, audio_path, output_path):
            await client.send_video(message.chat.id, output_path, reply_to_message_id=message.message_id)
        else:
            await message.reply_text("Failed to synchronize video and audio.")
    except Exception as e:
        await message.reply_text(f"Error during synchronization: {e}")
    finally:
        # Clean up files
        for file_path in [video_path, audio_path, output_path]:
            if os.path.exists(file_path):
                os.remove(file_path)

@api.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    asyncio.run(app.process_updates(data))
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run()
