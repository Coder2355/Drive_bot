import os
import subprocess
from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN
from pyngrok import ngrok

# Create download directory
DOWNLOAD_DIR = "/content/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Initialize Pyrogram client
app = Client("torrent_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.text & ~filters.edited)
async def torrent_handler(client, message):
    if message.text.startswith("magnet:") or message.text.endswith(".torrent"):
        await message.reply("Send `/torrent` to start leeching this link.", quote=True)

@app.on_message(filters.command("torrent"))
async def start_torrent_download(client, message):
    original_message = message.reply_to_message

    if not original_message or not (original_message.text.startswith("magnet:") or original_message.text.endswith(".torrent")):
        await message.reply("Reply to a valid magnet link or torrent file message with `/torrent`.")
        return

    torrent_link = original_message.text
    await message.reply("Starting torrent download...")

    try:
        # Start downloading with aria2c
        subprocess.run(
            ["aria2c", "--dir", DOWNLOAD_DIR, torrent_link],
            check=True
        )
        await message.reply("Torrent download complete! Uploading files...")

        for root, dirs, files in os.walk(DOWNLOAD_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                await client.send_document(message.chat.id, file_path)

        await message.reply("All files have been uploaded!")
    except subprocess.CalledProcessError:
        await message.reply("Failed to download the torrent.")

# Start the bot
if __name__ == "__main__":
    app.run()
