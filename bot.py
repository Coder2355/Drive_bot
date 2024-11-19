import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, RPCError
from config import API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNEL_ID

# Initialize global variable for the target channel
TARGET_CHANNEL_ID = None  # Default to None

app = Client("video_forward_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# Progress bar function
async def progress_bar(current, total, message, status_text):
    percentage = (current / total) * 100
    progress = f"{status_text}: {percentage:.2f}% ({current}/{total} bytes)"
    await message.edit(progress)


# Function to check if the bot is an admin in a channel
async def check_bot_admin_status(client, channel_id):
    try:
        member = await client.get_chat_member(chat_id=channel_id, user_id=client.me.id)
        return member.can_post_messages  # Checks if the bot has admin privileges
    except RPCError:
        return False


# Command to set the target channel
@app.on_message(filters.command("set_target") & filters.user([YOUR_USER_ID]))  # Replace YOUR_USER_ID with your Telegram ID
async def set_target_channel(client, message: Message):
    global TARGET_CHANNEL_ID
    if len(message.command) < 2:
        await message.reply("**Usage:** /set_target <channel_id>")
        return

    try:
        # Parse the target channel ID
        new_target_channel = int(message.command[1])

        # Check bot admin status in the target channel
        is_admin = await check_bot_admin_status(client, new_target_channel)
        if not is_admin:
            chat = await client.get_chat(new_target_channel)
            await message.reply(f"**Error:** Please make the bot an admin in `{chat.title}` before setting it as the target channel.")
            return

        # Update the global variable
        TARGET_CHANNEL_ID = new_target_channel
        # Fetch the channel name for confirmation
        chat = await client.get_chat(new_target_channel)
        await message.reply(f"**Target channel changed to:** {chat.title} ({new_target_channel})")
    except ValueError:
        await message.reply("**Error:** Invalid channel ID. Please provide a valid integer.")
    except Exception as e:
        await message.reply(f"**Error:** {e}")


# Process videos uploaded to the source channel
@app.on_message(filters.chat(SOURCE_CHANNEL_ID) & filters.video)
async def process_video(client, message: Message):
    global TARGET_CHANNEL_ID
    if not TARGET_CHANNEL_ID:
        await message.reply("**Error:** Target channel not set. Use /set_target to set the channel.")
        return

    try:
        # Check bot admin status in the target channel
        is_admin = await check_bot_admin_status(client, TARGET_CHANNEL_ID)
        if not is_admin:
            chat = await client.get_chat(TARGET_CHANNEL_ID)
            await message.reply(f"**Error:** Please make the bot an admin in `{chat.title}`.")
            return

        # Initial message in the target channel
        status_message = await app.send_message(
            chat_id=TARGET_CHANNEL_ID,
            text="**Downloading the file...**",
        )

        # Download the video with progress
        video_path = await message.download(
            progress=progress_bar,
            progress_args=(status_message, "Downloading"),
        )

        # Renaming the file
        await status_message.edit("**Renaming the file...**")
        new_name = f"Renamed_{os.path.basename(video_path)}"
        renamed_path = os.path.join(os.path.dirname(video_path), new_name)
        os.rename(video_path, renamed_path)

        # Upload the video with progress
        await status_message.edit("**Uploading the file...**")
        await app.send_video(
            chat_id=TARGET_CHANNEL_ID,
            video=renamed_path,
            caption=f"**Renamed File:** {new_name}",
            progress=progress_bar,
            progress_args=(status_message, "Uploading"),
        )

        # Cleanup and final message
        os.remove(renamed_path)
        await status_message.edit("**File uploaded successfully!**")
        await asyncio.sleep(5)
        await status_message.delete()

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        await app.send_message(chat_id=TARGET_CHANNEL_ID, text=f"**Error:** {e}")


# Start the bot
if __name__ == "__main__":
    app.run()
