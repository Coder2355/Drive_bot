import asyncio
from pyrogram import Client, filters
from aiohttp import web
from config import config
from callback import start, merge_command, receive_video, receive_audio

app = Client(
    "media_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Registering the callbacks from callback.py using decorators
@app.on_message(filters.command("start"))
async def on_start(client, message):
    await start(client, message)

@app.on_message(filters.command("merge"))
async def on_merge(client, message):
    await merge_command(client, message)

@app.on_message((filters.video | filters.document) & filters.private)
async def on_receive_video(client, message):
    await receive_video(client, message)

@app.on_message(filters.audio & filters.private)
async def on_receive_audio(client, message):
    await receive_audio(client, message)


if __name__ == "__main__":
    app.run()
