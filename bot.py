import os
import time
import libtorrent as lt
from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("torrent_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOAD_DIR = "./downloads"  # Directory to save downloaded files

# Ensure the download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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
    await message.reply("Starting the torrent download...")

    # Initialize session and add torrent
    session = lt.session()
    session.listen_on(6881, 6891)
    params = {
        "save_path": DOWNLOAD_DIR,
        "storage_mode": lt.storage_mode_t.storage_mode_sparse,
    }

    if torrent_link.startswith("magnet:"):
        handle = lt.add_magnet_uri(session, torrent_link, params)
    else:
        handle = lt.add_torrent_params(params)
        with open(torrent_link, "rb") as f:
            handle.torrent_data = f.read()

    session.add_torrent(handle)
    await message.reply("Torrent added. Downloading...")

    # Monitor progress
    while not handle.is_seed():
        status = handle.status()
        progress = round(status.progress * 100, 2)
        speed = round(status.download_rate / 1024, 2)  # KB/s
        await message.edit_text(f"Downloading... {progress}% @ {speed} KB/s")
        time.sleep(5)

    # Upload completed files
    await message.reply("Download complete! Uploading files...")

    for root, dirs, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            await client.send_document(message.chat.id, file_path)

    await message.reply("All files have been uploaded!")

# Run the bot
if __name__ == "__main__":
    app.run()
