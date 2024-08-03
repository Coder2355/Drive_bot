import os
import asyncio
import aiohttp
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import Message
import ffmpeg
from multiprocessing import Process
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_PATH, PROCESSED_PATH

app = Client("gdrive_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
web_app = Flask(__name__)

async def download_from_gdrive(url: str, dest: str):
    gdrive_base_url = "https://drive.google.com/uc?export=download"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={'id': get_gdrive_file_id(url)}, stream=True) as response:
            token = get_confirm_token(response)

            if token:
                async with session.get(url, params={'id': get_gdrive_file_id(url), 'confirm': token}, stream=True) as response:
                    await save_response_content(response, dest)
            else:
                await save_response_content(response, dest)

def get_gdrive_file_id(url: str) -> str:
    if 'id=' in url:
        return url.split('id=')[1]
    elif 'drive.google.com' in url:
        return url.split('/')[-2]
    else:
        raise ValueError("Invalid Google Drive URL")

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    return None

async def save_response_content(response, dest):
    CHUNK_SIZE = 32768
    with open(dest, 'wb') as f:
        async for chunk in response.content.iter_chunked(CHUNK_SIZE):
            if chunk:
                f.write(chunk)

def process_video(input_path: str, output_path: str):
    ffmpeg.input(input_path).output(output_path).run()

@app.on_message(filters.command("upload") & filters.private)
async def upload(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide a Google Drive URL.")
        return

    gdrive_url = message.command[1]

    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    if not os.path.exists(PROCESSED_PATH):
        os.makedirs(PROCESSED_PATH)

    video_path = os.path.join(DOWNLOAD_PATH, "video.mp4")
    processed_path = os.path.join(PROCESSED_PATH, "processed_video.mp4")

    try:
        await message.reply_text("Downloading video from Google Drive...")
        await download_from_gdrive(gdrive_url, video_path)

        await message.reply_text("Processing video with FFmpeg...")
        process_video(video_path, processed_path)

        await message.reply_text("Uploading processed video...")
        await client.send_video(message.chat.id, processed_path)
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(processed_path):
            os.remove(processed_path)

@web_app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        gdrive_url = request.form['gdrive_url']
        chat_id = request.form['chat_id']

        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH)

        if not os.path.exists(PROCESSED_PATH):
            os.makedirs(PROCESSED_PATH)

        video_path = os.path.join(DOWNLOAD_PATH, "video.mp4")
        processed_path = os.path.join(PROCESSED_PATH, "processed_video.mp4")

        async def handle_web_request():
            try:
                await download_from_gdrive(gdrive_url, video_path)
                process_video(video_path, processed_path)
                await app.send_video(chat_id, processed_path)
            except Exception as e:
                return f"An error occurred: {str(e)}"
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(processed_path):
                    os.remove(processed_path)

        asyncio.run(handle_web_request())

        return "Video processed and sent to Telegram!"
    return '''
    <form method="post">
        Google Drive URL: <input type="text" name="gdrive_url"><br>
        Telegram Chat ID: <input type="text" name="chat_id"><br>
        <input type="submit" value="Upload">
    </form>
    '''

if __name__ == "__main__":
    app.run()
