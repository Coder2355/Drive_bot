import asyncio
from pyrogram import Client
from aiohttp import web
from config import config
from callback import start, merge_command, receive_video, receive_audio

app = Client(
    "media_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Registering the callbacks from callback.py
app.add_handler(filters.command("start")(start))
app.add_handler(filters.command("merge")(merge_command))
app.add_handler((filters.video | filters.document) & filters.private)(receive_video)
app.add_handler(filters.audio & filters.private)(receive_audio)


if __name__ == "__main__":
    app.run()
