import os
import asyncio
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("stream_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store stream selection
stream_selection = {}

async def progress(current, total, message, status_message, process):
    try:
        progress_percentage = current * 100 / total
        progress_text = f"{status_message}: {progress_percentage:.1f}%\n"
        progress_text += f"{current / 1024 / 1024:.1f}MB of {total / 1024 / 1024:.1f}MB"

        # Edit the status message with the updated progress
        await process.edit_text(progress_text)
    except MessageNotModified:
        pass  # Handle case when message is not modified (e.g., same progress)

def extract_video_duration(file_path):
    """Extracts the duration of the video."""
    metadata = extractMetadata(createParser(file_path))
    duration = 0
    if metadata and metadata.has("duration"):
        duration = metadata.get("duration").seconds
    return duration

def take_screenshot(file_path, timestamp, output_image):
    """Takes a screenshot from the video at a given timestamp."""
    (
        ffmpeg
        .input(file_path, ss=timestamp)
        .output(output_image, vframes=1)
        .run(overwrite_output=True)
    )

@app.on_message(filters.command("stream_remove") & filters.reply)
async def stream_remove(client, message):
    # Send a message indicating download status
    status_message = await message.reply("📥 Downloading video file...")

    # Download the video file with progress
    video_message = message.reply_to_message
    file_path = await video_message.download(progress=progress, message=video_message, status_message="Downloading", process=status_message)

    # Extract video duration
    duration = extract_video_duration(file_path)

    # Update the status message to indicate download completion
    await status_message.edit_text("📥 Video downloaded successfully. Analyzing streams...")

    # Retrieve streams info from the video using ffmpeg
    streams = ffmpeg.probe(file_path)["streams"]

    # Create inline buttons for each stream
    buttons = []
    for index, stream in enumerate(streams):
        lang = stream.get("tags", {}).get("language", "unknown")
        codec_type = stream["codec_type"]
        button_text = f"{index + 1} {lang} {'🎵' if codec_type == 'audio' else '📜'}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"toggle_{index}")])

    buttons.append([InlineKeyboardButton("Reverse Selection", callback_data="reverse_selection")])
    buttons.append([InlineKeyboardButton("Cancel", callback_data="cancel"), InlineKeyboardButton("Done", callback_data="done")])

    # Send the buttons to the user
    await status_message.edit_text(
        "Okay, Now Select All The Streams You Want To Remove From Media. You Have 5 Minutes",
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
        lang = streams[index].get("tags", {}).get("language", "unknown")
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
    thumbnail_path = "thumbnail.jpg"

    # Take a screenshot at the halfway point
    screenshot_timestamp = duration // 2  # Take screenshot at the midpoint of the video
    take_screenshot(file_path, screenshot_timestamp, thumbnail_path)

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
        duration=duration,
        progress=progress,
        message=message,
        status_message="Uploading",
        process=status_message
    )

    # Cleanup
    os.remove(file_path)
    os.remove(output_file)
    os.remove(thumbnail_path)
    del stream_selection[user_id]

    # Update the status to indicate completion
    await status_message.edit_text("✅ Processing and upload complete!")

app.run()
