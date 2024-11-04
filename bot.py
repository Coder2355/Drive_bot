import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import ffmpeg
from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

DOWNLOAD_DIR = './downloads/'

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
    app.user_data[user_id] = {
        "file_path": file_path,
        "streams": streams,
        "selected_streams": set()
    }

    # Step 4: Show inline keyboard with stream options
    await update_stream_buttons(client, message, user_id)

async def update_stream_buttons(client, message, user_id):
    user_data = app.user_data[user_id]
    streams = user_data["streams"]
    selected_streams = user_data["selected_streams"]

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
    user_data = app.user_data.get(user_id, {})

    if not user_data:
        await callback_query.answer("No operation found.")
        return

    data = callback_query.data
    if data == "cancel":
        await callback_query.message.edit_text("Operation cancelled.")
        os.remove(user_data["file_path"])
        app.user_data.pop(user_id, None)

    elif data == "reverse":
        all_streams = set([s[0] for s in user_data["streams"]])
        selected = user_data["selected_streams"]
        user_data["selected_streams"] = all_streams - selected
        await update_stream_buttons(client, callback_query.message, user_id)
        await callback_query.answer("Selection reversed.")

    elif data == "done":
        if not user_data["selected_streams"]:
            await callback_query.answer("No streams selected.")
            return
        await callback_query.message.edit_text("Processing the video...")
        await remove_selected_streams(callback_query.message, user_data)

    elif data.startswith("toggle_"):
        # Toggle the selection state for a stream
        stream_id = int(data.split("_")[1])
        if stream_id in user_data["selected_streams"]:
            user_data["selected_streams"].remove(stream_id)
        else:
            user_data["selected_streams"].add(stream_id)
        await update_stream_buttons(client, callback_query.message, user_id)
        await callback_query.answer("Stream selection updated.")

async def remove_selected_streams(message, user_data):
    file_path = user_data["file_path"]
    selected_streams = user_data["selected_streams"]

    # Prepare FFmpeg command to remove selected streams
    output_file = file_path.replace(".mp4", "_no_streams.mp4")
    ffmpeg_cmd = (
        ffmpeg.input(file_path)
        .output(output_file, map=f"!{','.join(str(s) for s in selected_streams)}")
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )
    await ffmpeg_cmd.communicate()

    # Send the output file back to the user
    await message.reply_video(output_file)
    os.remove(file_path)
    os.remove(output_file)
    app.user_data.pop(message.chat.id, None)

app.run()
