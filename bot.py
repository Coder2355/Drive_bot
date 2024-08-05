import os
import ffmpeg
import threading
from flask import Flask, request, jsonify
from pyrogram import Client, filters
from pyrogram.types import InputMediaAudio, InputMediaVideo
from tqdm import tqdm
import config

# Initialize the Flask app
flask_app = Flask(__name__)

# Initialize the bot
app = Client("my_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

# Create folders to save downloaded files
os.makedirs("downloads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Function to display a progress bar for file download
def progress_bar(current, total, text="Downloading"):
    progress = tqdm(total=total, initial=current, desc=text, unit='B', unit_scale=True, leave=False)
    progress.update(current - progress.n)
    progress.close()

# Function to display a progress bar for file upload
def upload_progress_bar(current, total):
    progress_bar(current, total, text="Uploading")

@app.on_message(filters.command("trim_audio") & filters.audio)
async def trim_audio(client, message):
    if len(message.command) != 3:
        await message.reply("Usage: /trim_audio start_time end_time\nExample: /trim_audio 00:00:10 00:00:20")
        return

    start_time, end_time = message.command[1], message.command[2]

    audio_file = await message.download(file_name="downloads/", progress=progress_bar)
    output_file = f"outputs/trimmed_{os.path.basename(audio_file)}"

    (
        ffmpeg
        .input(audio_file, ss=start_time, to=end_time)
        .output(output_file)
        .run()
    )

    await message.reply_audio(output_file, progress=upload_progress_bar)
    os.remove(audio_file)
    os.remove(output_file)

@app.on_message(filters.command("merge") & filters.video & filters.reply)
async def merge_audio_video(client, message):
    if not message.reply_to_message.audio:
        await message.reply("Please reply to a video with an audio file and use the /merge command.")
        return

    video_file = await message.download(file_name="downloads/", progress=progress_bar)
    audio_file = await message.reply_to_message.download(file_name="downloads/", progress=progress_bar)
    output_file = f"outputs/merged_{os.path.basename(video_file)}"

    (
        ffmpeg
        .input(video_file)
        .input(audio_file)
        .output(output_file, vcodec='copy', acodec='aac')
        .run()
    )

    await message.reply_video(output_file, progress=upload_progress_bar)
    os.remove(video_file)
    os.remove(audio_file)
    os.remove(output_file)

@app.on_message(filters.command("merge_audio") & filters.audio)
async def merge_audio(client, message):
    if 'first_audio' not in client.data:
        client.data['first_audio'] = message
        await message.reply("Audio file received. Please send the second audio file.")
    elif 'second_audio' not in client.data:
        client.data['second_audio'] = message
        await message.reply("Second audio file received. Merging audio files...")
        await merge_audio_files(client)
    else:
        await message.reply("You have already provided two audio files. Please use /merge_audio to start over.")

async def merge_audio_files(client):
    first_audio = await client.data['first_audio'].download(file_name="downloads/")
    second_audio = await client.data['second_audio'].download(file_name="downloads/")
    output_file = f"outputs/merged_audio_{os.path.basename(first_audio)}"

    (
        ffmpeg
        .concat(
            ffmpeg.input(first_audio),
            ffmpeg.input(second_audio),
            v=0, a=1
        )
        .output(output_file)
        .run()
    )

    await client.data['first_audio'].reply_audio(output_file, progress=upload_progress_bar)
    os.remove(first_audio)
    os.remove(second_audio)
    os.remove(output_file)
    
    client.data.clear()

@flask_app.route('/trim_audio', methods=['POST'])
def web_trim_audio():
    data = request.json
    audio_file = data['audio_file']
    start_time = data['start_time']
    end_time = data['end_time']
    
    audio_path = f"downloads/{os.path.basename(audio_file)}"
    output_file = f"outputs/trimmed_{os.path.basename(audio_file)}"

    (
        ffmpeg
        .input(audio_path, ss=start_time, to=end_time)
        .output(output_file)
        .run()
    )

    return jsonify({"output_file": output_file})

@flask_app.route('/merge', methods=['POST'])
def web_merge_audio_video():
    data = request.json
    video_file = data['video_file']
    audio_file = data['audio_file']
    
    video_path = f"downloads/{os.path.basename(video_file)}"
    audio_path = f"downloads/{os.path.basename(audio_file)}"
    output_file = f"outputs/merged_{os.path.basename(video_file)}"

    (
        ffmpeg
        .input(video_path)
        .input(audio_path)
        .output(output_file, vcodec='copy', acodec='aac')
        .run()
    )

    return jsonify({"output_file": output_file})

if __name__ == "__main__":
    app.run()
