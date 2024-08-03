import os
import re
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from tqdm.asyncio import tqdm
import config

# Initialize Pyrogram Client
app = Client("gdrive_url_uploader_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

# Initialize Google Drive API Client
credentials = service_account.Credentials.from_service_account_file(config.GDRIVE_CREDENTIALS)
drive_service = build('drive', 'v3', credentials=credentials)

# Helper function to get Google Drive file ID from URL
def get_file_id(url):
    pattern = r'(?:https://drive.google.com/file/d/|https://drive.google.com/open\?id=)([^/]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

async def download_file(file_id, file_name, message, client):
    request = drive_service.files().get_media(fileId=file_id)
    fh = open(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    total_size = int(request.headers['Content-Length'])
    chunk_size = 1024 * 1024  # 1 MB
    progress = tqdm(total=total_size, unit='B', unit_scale=True, desc=file_name)

    while not done:
        status, done = downloader.next_chunk(chunk_size=chunk_size)
        progress.update(chunk_size)
        progress.n = min(progress.total, progress.n + chunk_size)
        progress.refresh()
        await client.send_chat_action(message.chat.id, "upload_document")

    progress.close()
    fh.close()

# Command handler to upload Google Drive files
@app.on_message(filters.command("upload") & filters.private)
async def upload_gdrive_file(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide a Google Drive URL.")
        return

    url = message.command[1]
    file_id = get_file_id(url)
    
    if not file_id:
        await message.reply_text("Invalid Google Drive URL.")
        return

    try:
        # Get file metadata
        file = drive_service.files().get(fileId=file_id).execute()
        file_name = file.get('name')
        
        await message.reply_text(f"Downloading file: {file_name}")

        # Download file with progress bar
        await download_file(file_id, file_name, message, client)
        
        await message.reply_text(f"File downloaded: {file_name}")

        # Upload to Telegram
        await client.send_document(chat_id=message.chat.id, document=file_name)
        os.remove(file_name)
    except Exception as e:
        await message.reply_text(f"Failed to upload file: {e}")

# Start the bot with long polling
if __name__ == "__main__":
    app.run()
