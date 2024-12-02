import asyncio
import libtorrent as lt
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# Config
DOWNLOAD_PATH = "./downloads/"

# Initialize the bot
bot = Client("torrent_downloader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def download_torrent(torrent_link):
    """Download torrent file using libtorrent."""
    session = lt.session()
    session.listen_on(6881, 6891)

    params = {
        'save_path': DOWNLOAD_PATH,
        'storage_mode': lt.storage_mode_t.storage_mode_allocate,
    }

    handle = lt.add_magnet_uri(session, torrent_link, params)
    session.start_dht()

    print("Downloading metadata...")
    while not handle.has_metadata():
        time.sleep(1)

    print("Metadata downloaded. Starting torrent download.")
    while not handle.is_seed():
        status = handle.status()
        print(f"\rProgress: {status.progress * 100:.2f}% | Download rate: {status.download_rate / 1000:.2f} kB/s | "
              f"Upload rate: {status.upload_rate / 1000:.2f} kB/s", end="")
        time.sleep(1)

    print("\nTorrent download completed!")
    return handle


async def upload_to_telegram(file_path, message: Message):
    """Upload a file to Telegram with a progress bar."""
    async def progress(current, total):
        await message.edit_text(f"Uploading: {current * 100 / total:.1f}%")

    await message.reply_document(file_path, progress=progress)


@bot.on_message(filters.command("torrent") & filters.reply)
async def torrent_download(_, message: Message):
    """Handle the /torrent command."""
    if not message.reply_to_message.text:
        await message.reply("Please reply to a valid torrent magnet link.")
        return

    magnet_link = message.reply_to_message.text.strip()
    if not magnet_link.startswith("magnet:?"):
        await message.reply("Invalid magnet link. Please provide a valid magnet link.")
        return

    await message.reply("Starting torrent download...")
    try:
        handle = download_torrent(magnet_link)
        torrent_info = handle.get_torrent_info()
        file_name = torrent_info.files()[0].path
        file_path = f"{DOWNLOAD_PATH}/{file_name}"

        await message.reply("Torrent downloaded successfully. Uploading to Telegram...")
        await upload_to_telegram(file_path, message)

    except Exception as e:
        await message.reply(f"An error occurred: {e}")


if __name__ == "__main__":
    print("Starting bot...")
    bot.run()
