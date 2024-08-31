import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import subprocess
from config import API_ID, API_HASH, BOT_TOKEN

app = Client("stream_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Directory to save downloaded files
DOWNLOAD_DIR = "downloads"

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def list_streams(file_path):
    """Function to list streams in the video file."""
    result = subprocess.run(
        ["ffmpeg", "-i", file_path], stderr=subprocess.PIPE, universal_newlines=True
    )
    output = result.stderr
    streams = []
    for line in output.splitlines():
        if "Stream #" in line:
            stream_info = line.split("Stream #")[1]
            stream_id = stream_info.split(":")[0]
            stream_description = stream_info.split(": ")[1]
            streams.append({"id": stream_id, "description": stream_description})
    return streams


def remove_streams(file_path, streams_to_remove):
    """Function to remove selected streams."""
    cmd = ["ffmpeg", "-i", file_path]
    
    for stream in streams_to_remove:
        cmd.extend(["-map", f"-0:{stream}"])
    
    output_file = f"{file_path.rsplit('.', 1)[0]}_no_streams.mkv"
    cmd.extend(["-c", "copy", output_file])
    
    subprocess.run(cmd)
    return output_file


@app.on_message(filters.command("stream_remove") & filters.reply)
async def stream_remover(client: Client, message: Message):
    msg = message.reply_to_message
    if not (msg.video or msg.document):
        await message.reply("Please reply to a video or document file.")
        return

    msg_reply = await message.reply("Downloading the file...")
    file_path = await msg.download(DOWNLOAD_DIR)
    await msg_reply.edit("File downloaded. Analyzing streams...")

    streams = list_streams(file_path)
    if not streams:
        await msg_reply.edit("No streams found.")
        return

    buttons = []
    for stream in streams:
        buttons.append([InlineKeyboardButton(f"{stream['description']}", callback_data=f"stream_{stream['id']}")])

    await msg_reply.edit(
        "Select the streams to remove:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    # Store the stream data in the message object
    message.user_data = {
        "file_path": file_path,
        "streams": streams,
        "streams_to_remove": [],
        "msg_reply": msg_reply
    }


@app.on_callback_query(filters.regex(r"^stream_"))
async def select_stream(client: Client, callback_query):
    message = callback_query.message
    data = callback_query.data
    stream_id = data.split("_")[1]

    user_data = message.reply_to_message.user_data

    # Toggle stream selection
    if stream_id in user_data["streams_to_remove"]:
        user_data["streams_to_remove"].remove(stream_id)
        new_text = callback_query.message.text.replace(f"✅ {stream_id}", stream_id)
    else:
        user_data["streams_to_remove"].append(stream_id)
        new_text = callback_query.message.text.replace(stream_id, f"✅ {stream_id}")

    await callback_query.answer()

    # Update the message with the selected streams
    await message.edit_text(new_text, reply_markup=callback_query.message.reply_markup)


@app.on_message(filters.command("confirm_remove") & filters.reply)
async def confirm_remove(client: Client, message: Message):
    user_data = message.reply_to_message.user_data

    if not user_data["streams_to_remove"]:
        await message.reply("No streams selected for removal.")
        return

    await user_data["msg_reply"].edit("Removing selected streams...")
    output_file = remove_streams(user_data["file_path"], user_data["streams_to_remove"])
    
    await user_data["msg_reply"].edit("Streams removed successfully. Uploading the file...")
    await message.reply_document(output_file)
    await user_data["msg_reply"].delete()

    # Cleanup
    os.remove(user_data["file_path"])
    os.remove(output_file)


app.run()
