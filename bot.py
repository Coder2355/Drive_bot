import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
import os
import ffmpeg
from config import API_ID, API_HASH, BOT_TOKEN

# Bot setup
app = Client("audio_merger_bot", api_id=YOUR_API_ID, api_hash=YOUR_API_HASH, bot_token=YOUR_BOT_TOKEN)

# Dictionary to store user state
user_state = {}

@app.on_message(filters.reply & filters.command("merge_audio"))
async def merge_audio_command(client, message):
    if message.reply_to_message.audio or (message.reply_to_message.document and message.reply_to_message.document.mime_type.startswith("audio/")):
        # Create inline keyboard button
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("audio+audio", callback_data="start_merge")]]
        )
        await message.reply_text("Press the button to start the merging process.", reply_markup=buttons)
        
        # Save the first audio file
        user_state[message.from_user.id] = {
            "first_audio": message.reply_to_message,
            "second_audio": None
        }
        print(f"First audio saved for user {message.from_user.id}")
    else:
        await message.reply_text("Please reply to an audio file or audio document file to start the merging process.")

@app.on_callback_query(filters.regex("start_merge"))
async def start_merge(client, callback_query):
    user_id = callback_query.from_user.id
    
    # Check if the user has started the merging process
    if user_id in user_state and user_state[user_id]["first_audio"]:
        await callback_query.message.reply_text(
            "Send the second audio file to merge it with the first one."
        )
        print(f"Asked user {user_id} for the second audio file")
    else:
        await callback_query.message.reply_text("Please start the merging process by replying to an audio file with /merge_audio.")

@app.on_message(filters.reply & (filters.audio | filters.document))
async def receive_second_audio(client, message):
    user_id = message.from_user.id

    print(f"Received a reply from user {user_id}")
    
    if user_id in user_state and user_state[user_id]["first_audio"] and not user_state[user_id]["second_audio"]:
        # Save the second audio file
        user_state[user_id]["second_audio"] = message
        
        # Notify the user that downloading is starting
        download_msg = await message.reply_text("Downloading audio files...")

        # Start downloading the first and second audio files
        first_audio_file = await user_state[user_id]["first_audio"].download()
        print(f"First audio file downloaded: {first_audio_file}")
        second_audio_file = await message.download()
        print(f"Second audio file downloaded: {second_audio_file}")

        # Notify the user that merging is starting
        await download_msg.edit_text("Merging audio files...")

        # Define the output file path
        output_file = f"merged_{message.from_user.id}.mp3"

        # Run FFmpeg to merge the two audio files
        await merge_audio_files(first_audio_file, second_audio_file, output_file)

        # Notify the user that uploading is starting
        upload_msg = await message.reply_text("Uploading merged audio file...")

        # Send the merged file back to the user
        await message.reply_audio(output_file)
        
        # Cleanup: delete the downloaded and output files
        os.remove(first_audio_file)
        os.remove(second_audio_file)
        os.remove(output_file)

        # Notify the user that the process is complete
        await upload_msg.edit_text("Merging and uploading completed!")

        # Clear user state
        user_state.pop(user_id)

async def merge_audio_files(first_file, second_file, output_file):
    await asyncio.create_subprocess_exec(
        'ffmpeg', '-i', first_file, '-i', second_file, '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[out]', '-map', '[out]', output_file
    )

if __name__ == "__main__":
    app.run()
