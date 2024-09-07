import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import ffmpeg

from config import API_ID, API_HASH, BOT_TOKEN

app = Client("stream_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# Store user selections (a dictionary to store selections based on user IDs)
user_selections = {}

@app.on_message(filters.command("stream_rem") & filters.reply)
async def stream_remover(client, message):
    # Download the video/document
    reply_message = message.reply_to_message
    file_path = await reply_message.download()

    # Extract the streams using FFmpeg
    streams = extract_streams(file_path)
    
    if streams:
        # Build the keyboard with stream options
        keyboard = []
        for idx, stream in enumerate(streams, 1):
            keyboard.append([InlineKeyboardButton(f"{idx} {stream}", callback_data=f"stream_{idx}")])
        
        # Add Done and Cancel buttons
        keyboard.append([InlineKeyboardButton("Done ✅", callback_data="done"), InlineKeyboardButton("Cancel ❌", callback_data="cancel")])

        # Send a message with the stream options
        await message.reply(
            "Okay, Now Select All The Streams You Want To Remove From Media.\nYou Have 5 Minutes",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Save the file path and stream info for the user
        user_selections[message.from_user.id] = {"file_path": file_path, "streams": streams, "selected_streams": []}

def extract_streams(file_path):
    """
    Extract streams from the video using FFmpeg.
    """
    streams = []
    try:
        # Use FFmpeg to extract stream details
        probe = ffmpeg.probe(file_path)
        for stream in probe['streams']:
            if stream['codec_type'] in ['audio', 'subtitle']:
                streams.append(f"{stream['tags'].get('language', 'unknown')} {stream['codec_name']}")
    except Exception as e:
        print(f"Error extracting streams: {e}")
    return streams

@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if user_id not in user_selections:
        await callback_query.answer("No active stream selection!")
        return

    if data.startswith("stream_"):
        # Stream selection handling
        stream_idx = int(data.split("_")[1]) - 1
        selected_streams = user_selections[user_id]["selected_streams"]

        if stream_idx in selected_streams:
            selected_streams.remove(stream_idx)  # Deselect
        else:
            selected_streams.append(stream_idx)  # Select

        # Update button text (add or remove checkmark)
        streams = user_selections[user_id]["streams"]
        keyboard = []
        for idx, stream in enumerate(streams, 1):
            if idx - 1 in selected_streams:
                keyboard.append([InlineKeyboardButton(f"{idx} {stream} ✅", callback_data=f"stream_{idx}")])
            else:
                keyboard.append([InlineKeyboardButton(f"{idx} {stream}", callback_data=f"stream_{idx}")])

        # Add Done and Cancel buttons
        keyboard.append([InlineKeyboardButton("Done ✅", callback_data="done"), InlineKeyboardButton("Cancel ❌", callback_data="cancel")])

        await callback_query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "done":
        # Process the selected streams
        file_path = user_selections[user_id]["file_path"]
        selected_streams = user_selections[user_id]["selected_streams"]
        streams = user_selections[user_id]["streams"]

        # Remove the selected streams
        await callback_query.answer("Processing your file, please wait...")
        output_file = await remove_streams(file_path, selected_streams, streams)

        # Upload the processed file
        await callback_query.message.reply_document(output_file)
        
        # Clean up
        os.remove(output_file)
        del user_selections[user_id]

    elif data == "cancel":
        # Cancel the operation
        await callback_query.answer("Operation canceled!")
        del user_selections[user_id]

async def remove_streams(file_path, selected_streams, streams):
    """
    Remove the selected streams from the video using FFmpeg.
    """
    output_file = file_path.replace(".mp4", "_modified.mp4")

    try:
        input_streams = []
        for idx, stream in enumerate(streams):
            if idx not in selected_streams:
                input_streams.append(f"-map 0:{idx}")

        # Use FFmpeg to remove selected streams
        cmd = f"ffmpeg -i {file_path} {' '.join(input_streams)} -c copy {output_file}"
        os.system(cmd)
    except Exception as e:
        print(f"Error removing streams: {e}")
    
    return output_file

# Run the bot
app.run()
