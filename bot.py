import os
import asyncio
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("stream_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store stream selection
stream_selection = {}

@app.on_message(filters.command("stream_remove") & filters.reply)
async def stream_remove(client, message):
    # Send a message indicating download status
    status_message = await message.reply("📥 Downloading video file...")
    
    # Download the video file
    video_message = message.reply_to_message
    file_path = await video_message.download()

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
    status_message = stream_selection["status_message"]
    output_file = "output_" + os.path.basename(file_path)

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

    # Upload the processed video
    await message.reply_document(output_file)

    # Cleanup
    os.remove(file_path)
    os.remove(output_file)
    del stream_selection[user_id]

    # Update the status to indicate completion
    await status_message.edit_text("✅ Processing and upload complete!")

app.run()
