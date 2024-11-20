from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from helper.utils import progress_for_pyrogram, humanbytes, convert
import os, time

# Global Variables
user_details = {}
TARGET_CHANNEL_ID = None

# Set Target Channel
@Client.on_message(filters.command("set_target") & filters.user(Config.ADMIN))
async def set_target_channel(client, message):
    global TARGET_CHANNEL_ID

    if len(message.command) > 1:
        try:
            TARGET_CHANNEL_ID = int(message.command[1])
            await message.reply("✅ Target channel added successfully!")
        except ValueError:
            await message.reply("❌ Invalid channel ID. Please provide a valid ID.")
    else:
        await message.reply("❓ Please provide a channel ID after the command. Example: `/set_target 123456789`")

# Handle File Upload and Rename
@Client.on_message(filters.private & (filters.document | filters.video) & filters.user(Config.ADMIN))
async def rename_start(client, message):
    file = getattr(message, message.media.value)
    filename = file.file_name

    if file.file_size > 2000 * 1024 * 1024:
        return await message.reply_text("❌ Sorry, this bot doesn't support files larger than 2GB.")

    user_id = message.chat.id
    user_details[user_id] = {"filename": filename, "file_id": file.file_id}

    try:
        await message.reply_text(
            text=f"**Please Enter New Filename...**\n\n**Old File Name:** `{filename}`",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(True)
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.private & filters.reply)
async def refunc(client, message):
    reply_message = message.reply_to_message
    if reply_message.reply_markup and isinstance(reply_message.reply_markup, ForceReply):
        user_id = message.chat.id
        new_name = message.text

        if not "." in new_name:
            ext = os.path.splitext(user_details[user_id]["filename"])[-1]
            new_name = new_name + ext

        user_details[user_id]["new_name"] = new_name
        await reply_message.delete()

        buttons = [
            [InlineKeyboardButton("📁 Document", callback_data="upload_document")],
            [InlineKeyboardButton("🎥 Video", callback_data="upload_video")]
        ]
        await message.reply(
            text=f"**Select the Output File Type**\n\n**File Name:** `{new_name}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

@Client.on_callback_query(filters.regex("upload"))
async def upload_file(client, query):
    global TARGET_CHANNEL_ID

    user_id = query.message.chat.id
    user_data = user_details.get(user_id)

    if not user_data or "filename" not in user_data or "file_id" not in user_data:
        return await query.message.edit("❌ Error: Missing file information. Please restart the process.")

    old_filename = user_data["filename"]
    new_filename = user_data.get("new_name", old_filename)
    file_id = user_data["file_id"]
    file_path = f"downloads/{user_id}/{new_filename}"

    # Notify Target Channel
    if not TARGET_CHANNEL_ID:
        return await query.message.edit("❌ Error: Target channel not set. Use `/set_target` to set the channel.")

    target_msg = await client.send_message(
        chat_id=TARGET_CHANNEL_ID,
        text=f"⬇️ **Starting download...**\n\n📁 **Filename:** `{new_filename}`"
    )

    # Download File with Progress
    start_time = time.time()
    try:
        downloaded_path = await client.download_media(
            file_id,
            file_name=file_path,
            progress=progress_for_pyrogram,
            progress_args=("⬇️ **Downloading...**", target_msg, start_time)
        )
    except Exception as e:
        return await target_msg.edit(f"❌ Download failed: `{str(e)}`")

    # Notify Completion
    await target_msg.edit("✅ **Download complete! Proceeding to upload...**")

    # Upload File
    await query.message.edit("⬆️ **Uploading file...**")
    upload_type = query.data.split("_")[1]

    try:
        if upload_type == "document":
            await client.send_document(
                chat_id=TARGET_CHANNEL_ID,
                document=downloaded_path,
                caption=f"**{new_filename}**",
                progress=progress_for_pyrogram,
                progress_args=("⬆️ **Uploading...**", target_msg, start_time)
            )
        elif upload_type == "video":
            await client.send_video(
                chat_id=TARGET_CHANNEL_ID,
                video=downloaded_path,
                caption=f"**{new_filename}**",
                progress=progress_for_pyrogram,
                progress_args=("⬆️ **Uploading...**", target_msg, start_time)
            )
    except Exception as e:
        await target_msg.edit(f"❌ Upload failed: `{str(e)}`")
    else:
        await target_msg.edit("✅ **Upload complete!**")
    finally:
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)
