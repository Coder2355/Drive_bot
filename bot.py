import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIR

# Initialize the bot with your API credentials
app = Client("audio_merger_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Store the first audio file's message details
audio_storage = {}

@app.on_message(filters.command("merge_audio") & filters.reply)
async def merge_audio_command(client: Client, message: Message):
    if message.reply_to_message.audio or message.reply_to_message.document:
        # Send downloading message
        downloading_message = await message.reply_text("Downloading the first audio...")

        # Download the first audio
        audio_id = message.reply_to_message.id
        first_audio_path = await client.download_media(message.reply_to_message, file_name=os.path.join(DOWNLOAD_DIR, f"audio1_{audio_id}.mp3"))
        
        # Store the path of the first audio and the chat_id
        audio_storage[message.chat.id] = {
            "first_audio": first_audio_path,
            "user_id": message.from_user.id
        }
        
        # Notify that the first audio has been downloaded
        await downloading_message.edit_text("First audio downloaded. Please send the second audio file.")

@app.on_message(filters.audio | filters.document)
async def process_second_audio(client: Client, message: Message):
    if message.chat.id in audio_storage and audio_storage[message.chat.id]["user_id"] == message.from_user.id:
        if message.audio or message.document:
            # Send downloading message
            downloading_message = await message.reply_text("Downloading the second audio...")

            # Download the second audio
            audio_id = message.id
            second_audio_path = await client.download_media(message, file_name=os.path.join(DOWNLOAD_DIR, f"audio2_{audio_id}.mp3"))
            
            # Notify that the second audio has been downloaded
            await downloading_message.edit_text("Second audio downloaded. Merging the audios...")

            first_audio_path = audio_storage[message.chat.id]["first_audio"]
            
            # Merge the two audio files using FFmpeg
            merged_audio_path = os.path.join(DOWNLOAD_DIR, f"merged_{message.chat.id}.mp3")
            (
                ffmpeg
                .concat(ffmpeg.input(first_audio_path), ffmpeg.input(second_audio_path), v=0, a=1)
                .output(merged_audio_path)
                .run(overwrite_output=True)
            )
            
            # Send uploading message
            uploading_message = await message.reply_text("Uploading the merged audio...")

            # Send the merged audio file
            await client.send_audio(chat_id=message.chat.id, audio=merged_audio_path, caption="Here's your merged audio!")
            
            # Notify that the upload is complete
            await uploading_message.delete()

            # Clean up
            os.remove(first_audio_path)
            os.remove(second_audio_path)
            os.remove(merged_audio_path)
            del audio_storage[message.chat.id]
        else:
            await message.reply_text("Please send a valid audio file or document.")
    else:
        await message.reply_text("No merge process is active. Please start a new one with /merge_audio.")

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text("Hello! Reply to an audio file or document with /merge_audio to start the merging process.")

app.run()
