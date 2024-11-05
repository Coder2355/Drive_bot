import os
import time
import asyncio
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from utils import progress_for_pyrogram  # Import the function
from config import BOT_TOKEN, API_ID, API_HASH

app = Client("audio_video_editor_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to store stream selection
stream_selection = {}

@app.on_message(filters.video | filters.document)
async def stream_remove(client, message):
    # Send a message indicating download status
    status_message = await message.reply("📥 Downloading video file...")

    # Download the video file with progress
    video_message = message.reply_to_message
    file_path = await video_message.download(progress=progress_for_pyrogram, progress_args=("📥 Downloading video file...", status_message, time.time()))

    # Update the status message to indicate download completion
    await status_message.edit_text("Analyzing the streams from your file 🎆...")

    # Retrieve streams info from the video using ffmpeg
    streams = ffmpeg.probe(file_path)["streams"]
    
    # Define the duration by looking at the first video stream's duration
    duration = next((stream.get("duration") for stream in streams if stream["codec_type"] == "video"), None)
    if duration is not None:
        duration = float(duration)  # Convert duration to a float if it's available as a string

    # Create inline buttons for each stream
    buttons = []
    for index, stream in enumerate(streams):
        lang = stream.get("tags", {}).get("language")
        if lang is None or not lang.isalpha():  # Validate the language code
            lang = "unknown"  # Default to 'unknown' if invalid

        codec_type = stream["codec_type"]
        button_text = f"{index + 1} {lang} {'🎵' if codec_type == 'audio' else '📜'}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"toggle_{index}")])

    buttons.append([InlineKeyboardButton("Reverse Selection", callback_data="reverse_selection")])
    buttons.append([InlineKeyboardButton("Cancel", callback_data="cancel"), InlineKeyboardButton("Done", callback_data="done")])

    # Send the buttons to the user
    await status_message.edit_text(
        "Now Select The Streams You Want To remove From Media.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # Store initial state
    stream_selection[message.chat.id] = [False] * len(streams)
    stream_selection["file_path"] = file_path
    stream_selection["duration"] = duration
    stream_selection["status_message"] = status_message

@app.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.message.chat.id
    data = callback_query.data

    # Handling stream selection
    if data.startswith("toggle_"):
        index = int(data.split("_")[1])
        stream_selection[user_id][index] = not stream_selection[user_id][index]
        await update_buttons(callback_query)

    # Handling reverse selection
    elif data == "reverse_selection":
        stream_selection[user_id] = [not selected for selected in stream_selection[user_id]]
        await update_buttons(callback_query)

    # Handling cancellation
    elif data == "cancel":
        await callback_query.message.edit_text("Stream selection canceled.")
        os.remove(stream_selection["file_path"])
        del stream_selection[user_id]

    # Handling completion
    elif data == "done":
        await callback_query.message.edit_text("⏳ Processing your video...")
        await process_video(client, callback_query.message, user_id)

async def update_buttons(callback_query):
    user_id = callback_query.message.chat.id
    message = callback_query.message
    streams = ffmpeg.probe(stream_selection["file_path"])["streams"]
    buttons = []

    for index, selected in enumerate(stream_selection[user_id]):
        lang = streams[index].get("tags", {}).get("language")
        if lang is None or not lang.isalpha():  # Validate the language code
            lang = "unknown"  # Default to 'unknown' if invalid

        codec_type = streams[index]["codec_type"]
        status = "✅" if selected else ""
        button_text = f"{index + 1} {lang} {'🎵' if codec_type == 'audio' else '📜'} {status}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"toggle_{index}")])

    buttons.append([InlineKeyboardButton("Reverse Selection", callback_data="reverse_selection")])
    buttons.append([InlineKeyboardButton("Cancel", callback_data="cancel"), InlineKeyboardButton("Done", callback_data="done")])

    await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))

async def process_video(client, message, user_id):
    selected_streams = stream_selection[user_id]
    file_path = stream_selection["file_path"]
    duration = stream_selection["duration"]
    status_message = stream_selection["status_message"]
    output_file = "output_" + os.path.basename(file_path)
    caption = f"Here is your Output file 🗃️🫡"
    thumbnail_path = "thumbnail.jpg"

    # Take a screenshot at the halfway point
    screenshot_timestamp = duration // 2  # Take screenshot at the midpoint of the video
    take_screenshot(file_path, screenshot_timestamp, thumbnail_path)

    # Ensure the thumbnail exists
    if not os.path.exists(thumbnail_path):
        thumbnail_path = None

    # Create a list of "-map" arguments
    map_args = []
    for index, keep in enumerate(selected_streams):
        if not keep:
            map_args.extend(["-map", f"-0:{index}"])

    # Run FFmpeg command
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", file_path,
        "-map", "0",
        "-c", "copy",
        "-map", "-0:d",
        "-map", "-0:s",
        *map_args,
        output_file
    )

    await process.communicate()

    # Update status to indicate upload
    await status_message.edit_text("📤 Uploading the processed video...")

    # Upload the processed video with the thumbnail and progress
    await client.send_video(
        chat_id=message.chat.id,
        video=output_file,
        thumb=thumbnail_path,
        caption=caption,
        progress=progress_for_pyrogram,
        progress_args=("📤Uploading the video..", status_message, time.time())
    )

    # Cleanup
    os.remove(file_path)
    os.remove(output_file)
    if thumbnail_path:
        os.remove(thumbnail_path)
    del stream_selection[user_id]

    # Update the status to indicate completion
    await status_message.edit_text("✅ Processing and upload complete!")

app.run()
