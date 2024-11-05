import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import ffmpeg
from config import BOT_TOKEN, API_ID, API_HASH

DOWNLOAD_DIR = './downloads/'

app = Client("stream_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Use a global dictionary to store user-specific data
user_data = {}

@app.on_message(filters.video | filters.document)
async def handle_stream_remover(client, message: Message):
    # Step 1: Download the file
    msg = await message.reply_text("Downloading file...")
    file_path = await message.download(file_name=DOWNLOAD_DIR)
    await msg.edit_text("File downloaded. Analyzing streams...")

    # Step 2: Get all audio/subtitle streams from the video file
    streams = []
    try:
        probe = ffmpeg.probe(file_path)
        for stream in probe['streams']:
            stream_type = stream['codec_type']
            if stream_type in ('audio', 'subtitle'):
                language = stream.get('tags', {}).get('language', 'unknown')
                codec = stream['codec_name']
                index = stream['index']
                streams.append((index, stream_type, language, codec))
    except Exception as e:
        await msg.edit_text("Error analyzing streams.")
        os.remove(file_path)
        return

    if not streams:
        await msg.edit_text("No removable streams found in the file.")
        os.remove(file_path)
        return

    # Step 3: Store data for callback handling
    user_id = message.chat.id
    user_data[user_id] = {
        "file_path": file_path,
        "streams": streams,
        "selected_streams": set()
    }

    # Step 4: Show inline keyboard with stream options
    await update_stream_buttons(client, message, user_id)

async def update_stream_buttons(client, message, user_id):
    data = user_data.get(user_id)
    if not data:
        return  # If no user data is found, exit

    streams = data["streams"]
    selected_streams = data["selected_streams"]

    # Create buttons with checkmarks for selected streams
    buttons = []
    for index, (stream_id, stream_type, language, codec) in enumerate(streams, start=1):
        checkmark = "✅" if stream_id in selected_streams else ""
        button = InlineKeyboardButton(
            f"{checkmark} {index} {language.capitalize()} {stream_type.capitalize()} ({codec})",
            callback_data=f"toggle_{stream_id}"
        )
        buttons.append([button])

    # Add control buttons
    buttons.append([
        InlineKeyboardButton("Reverse Selection", callback_data="reverse"),
        InlineKeyboardButton("Cancel", callback_data="cancel"),
    ])
    buttons.append([InlineKeyboardButton("Done", callback_data="done")])

    # Edit message with updated buttons
    await client.send_message(
        user_id,
        "Okay, Now Select All The Streams You Want To Remove From Media.\nYou Have 5 Minutes",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    user_id = callback_query.message.chat.id
    data = user_data.get(user_id)

    if not data:
        await callback_query.answer("No operation found.")
        return

    callback_data = callback_query.data
    if callback_data == "cancel":
        await callback_query.message.edit_text("Operation cancelled.")
        os.remove(data["file_path"])
        user_data.pop(user_id, None)

    elif callback_data == "reverse":
        all_streams = set([s[0] for s in data["streams"]])
        selected = data["selected_streams"]
        data["selected_streams"] = all_streams - selected
        await update_stream_buttons(client, callback_query.message, user_id)
        await callback_query.answer("Selection reversed.")

    elif callback_data == "done":
        if not data["selected_streams"]:
            await callback_query.answer("No streams selected.")
            return
        await callback_query.message.edit_text("Processing the video...")
        await remove_selected_streams(callback_query.message, data)

    elif callback_data.startswith("toggle_"):
        # Toggle the selection state for a stream
        stream_id = int(callback_data.split("_")[1])
        if stream_id in data["selected_streams"]:
            data["selected_streams"].remove(stream_id)
        else:
            data["selected_streams"].add(stream_id)
        await update_stream_buttons(client, callback_query.message, user_id)
        await callback_query.answer("Stream selection updated.")

async def remove_selected_streams(message, data):
    file_path = data["file_path"]
    output_file = os.path.join(DOWNLOAD_DIR, "output_" + os.path.basename(file_path))

    # Build FFmpeg command to remove selected streams
    ffmpeg_command = ffmpeg.input(file_path)
    for stream_id in data["selected_streams"]:
        ffmpeg_command = ffmpeg_command.output(output_file, map=f"!{stream_id}")

    # Execute FFmpeg command
    try:
        await asyncio.to_thread(ffmpeg_command.run, overwrite_output=True)
        await message.reply_document(output_file)
        os.remove(file_path)
        os.remove(output_file)
    except Exception as e:
        await message.reply_text("Error removing streams from video.")
        os.remove(file_path)
        if os.path.exists(output_file):
            os.remove(output_file)

    # Clear user data after process is complete
    user_data.pop(message.chat.id, None)

app.run()
