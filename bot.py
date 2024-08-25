import os
import tempfile
import subprocess
import sys
import time
import asyncio
import logging 
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
from pyrogram import Client, filters
from progress import progress_for_pyrogram
from pyrogram.errors import FloodWait
from PIL import Image, ImageDraw  # Importing PIL for image processing

app = Flask(__name__)

# Thread pool for async processing
executor = ThreadPoolExecutor(max_workers=4)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Pyrogram client
client = Client("video_trimmer_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

# Dictionary to keep track of user conversations
user_conversations = {}

def run_command(command):
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True, result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {e.stderr.decode('utf-8')}")
        return False, e.stderr.decode('utf-8')
      
def trim_video(input_file, start_time, end_time, output_file):
    command = [
        'ffmpeg', '-i', input_file,
        '-ss', start_time,
        '-to', end_time,
        '-c:v', 'copy',  # copy video stream
        '-c:a', 'copy',  # copy audio stream
        '-map_metadata', '0', '-movflags', 'use_metadata_tags',
        output_file
    ]
    success, output = run_command(command)
    if not success:
        print(f"Failed to trim video: {output}", file=sys.stderr)
    return success

async def get_video_details(file_path):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size', '-of', 'default=noprint_wrappers=1', file_path]
    success, output = run_command(command)
    if success:
        details = {}
        for line in output.splitlines():
            key, value = line.split('=')
            details[key] = value
        return details
    return None

def create_play_button_image():
    # Create a blank image with a transparent background
    size = (100, 100)
    play_button_img = Image.new("RGBA", size, (0, 0, 0, 0))

    # Draw a play button (triangle) on the image
    draw = ImageDraw.Draw(play_button_img)
    triangle = [(25, 20), (25, 80), (75, 50)]
    draw.polygon(triangle, fill="white")

    # Save the image as play_button.png
    play_button_path = tempfile.mktemp(suffix=".png")
    play_button_img.save(play_button_path)

    return play_button_path

def create_thumbnail(input_file, output_thumbnail, duration, size):
    # Extract a thumbnail from the video
    command_thumbnail = ['ffmpeg', '-i', input_file, '-ss', '00:00:05', '-vframes', '1', output_thumbnail]
    success, _ = run_command(command_thumbnail)
    
    if success:
        # Convert duration to MM:SS format
        total_seconds = int(duration)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        duration_text = f"{minutes:02}:{seconds:02}"

        # Calculate file size in MB
        size_mb = round(int(size) / (1024 * 1024), 2)
        size_text = f"{size_mb} MB"
        
        output_with_text = output_thumbnail.replace('.png', '_with_text.png')
        command_text = [
            'ffmpeg', '-i', output_thumbnail, '-vf',
            f"drawtext=text='{duration_text}':x=W-tw-10:y=10:fontcolor=white:fontsize=24, drawtext=text='{size_text}':x=W-tw-10:y=H-th-40:fontcolor=white:fontsize=24",
            output_with_text
        ]
        success, _ = run_command(command_text)
        
        if success:
            # Overlay play button
            play_button_path = create_play_button_image()  # Generate play button image
            final_output_thumbnail = output_thumbnail.replace('.png', '_final.png')
            command_overlay = [
                'ffmpeg', '-i', output_with_text, '-i', play_button_path, '-filter_complex',
                "overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2", final_output_thumbnail
            ]
            success, _ = run_command(command_overlay)
            
            if success:
                return final_output_thumbnail
    return None

@client.on_message(filters.command("start"))
async def start_message(client: Client, message):
    await message.reply_text("Send me a video to trim. Use `/trim` command to start the trimming process.")

@client.on_message(filters.command("trim"))
async def trim_command(client: Client, message):
    if message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document):
        user_conversations[message.from_user.id] = {"video": message.reply_to_message.video.file_id}
        await message.reply_text("Please enter the start time in the format `hh:mm:ss`.", reply_markup={"force_reply": True})
        return
    else:
        await message.reply_text("Reply to a video or document with the `/trim` command to start the trimming process.")

@client.on_message(filters.text & filters.reply)
async def handle_time_input(client: Client, message):
    user_id = message.from_user.id
    if user_id in user_conversations:
        if message.text.startswith("00:"):
            if "start_time" in user_conversations[user_id]:
                end_time = message.text
                file_id = user_conversations[user_id]["video"]
                file_path = await client.download_media(file_id)
                
                # Generate output file path
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_file_trimmed = tempfile.mktemp(suffix=f"_{base_name}_trimmed.mp4")

                future = executor.submit(trim_video, file_path, user_conversations[user_id]["start_time"], end_time, output_file_trimmed)
                success = future.result()

                if success:
                    details = await get_video_details(output_file_trimmed)
                    if details:
                        duration = details.get('duration', 'Unknown')
                        size = details.get('size', 'Unknown')
                        size_mb = round(int(size) / (1024 * 1024), 2)
                        duration_sec = round(float(duration))
                        caption = f"Here's your trimmed video file. Duration: {duration_sec} seconds. Size: {size_mb} MB"

                        # Create thumbnail with duration, size, and play button
                        thumbnail_path = tempfile.mktemp(suffix=f"_{base_name}_thumb.png")
                        thumbnail = await asyncio.get_event_loop().run_in_executor(executor, create_thumbnail, output_file_trimmed, thumbnail_path, duration, int(size))
                        
                        uploader = await message.reply_text("Uploading video...")

                        await client.send_video(
                            chat_id=message.chat.id,
                            video=output_file_trimmed,
                            caption=caption,
                            thumb=thumbnail,
                            duration=duration,
                            progress=progress_for_pyrogram,
                            progress_args=("Uploading Video...", uploader, time.time())
                        )
                    else:
                        await message.reply_text("Failed to retrieve video details.")
                else:
                    await message.reply_text("Failed to process the video. Please try again later.")
                
                # Clean up files
                try:
                    os.remove(file_path)
                except Exception as e:
                    logging.error(f"Failed to remove file: {file_path}. Error: {e}")

                try:
                    os.remove(output_file_trimmed)
                except Exception as e:
                    logging.error(f"Failed to remove file: {output_file_trimmed}. Error: {e}")
                
                del user_conversations[user_id]
            else:
                user_conversations[user_id]["start_time"] = message.text
                await message.reply_text("Start time received. Please enter the end time in the format `hh:mm:ss`.", reply_markup={"force_reply": True})
        else:
            await message.reply_text("Please enter the time in the format `hh:mm:ss`.")

# Run the client
client.run()
