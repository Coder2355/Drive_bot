from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
import subprocess
import os

# Initialize the bot
app = Client("video_trimmer_bot", api_id="YOUR_API_ID", api_hash="YOUR_API_HASH", bot_token="YOUR_BOT_TOKEN")

# States for conversation
START_TIME, END_TIME = range(2)

# Dictionary to keep track of user conversations
user_conversations = {}

# Function to trim video
def trim_video(input_path, start_time, end_time, output_path):
    command = [
        "ffmpeg",
        "-i", input_path,
        "-ss", start_time,
        "-to", end_time,
        "-c", "copy",
        output_path
    ]
    subprocess.run(command, check=True)

@app.on_message(filters.command("start"))
def start_message(client: Client, message: Message):
    message.reply("Send me a video to trim. After that, use `/trim` command to start the trimming process.")

@app.on_message(filters.command("trim"))
def trim_command(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.video:
        user_conversations[message.from_user.id] = {"video": message.reply_to_message.video.file_id}
        message.reply("Please enter the start time in the format `hh:mm:ss`.")
        app.send_message(message.chat.id, "Please enter the start time in the format `hh:mm:ss`.", reply_to_message_id=message.message_id)
        app.send_message(message.chat.id, "Waiting for start time...")
        return START_TIME
    else:
        message.reply("Reply to a video with the `/trim` command to start the trimming process.")

@app.on_message(filters.text & filters.reply)
def handle_time_input(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in user_conversations:
        if message.text.startswith("00:"):
            if user_conversations[user_id].get("start_time"):
                end_time = message.text
                file_id = user_conversations[user_id]["video"]
                file_path = app.download_media(file_id)
                
                # Generate output file path
                output_path = file_path.replace(".mp4", "_trimmed.mp4")

                try:
                    trim_video(file_path, user_conversations[user_id]["start_time"], end_time, output_path)
                    message.reply_document(output_path)
                except Exception as e:
                    message.reply(f"An error occurred: {str(e)}")
                finally:
                    os.remove(file_path)
                    os.remove(output_path)
                
                del user_conversations[user_id]
            else:
                user_conversations[user_id]["start_time"] = message.text
                message.reply("Start time received. Please enter the end time in the format `hh:mm:ss`.")
        else:
            message.reply("Please enter the time in the format `hh:mm:ss`.")

# Run the bot
app.run()
