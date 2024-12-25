import os
from pyrogram import Client, filters
from pyrogram.types import Message
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL

app = Client("FileStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@app.on_message(filters.private & (filters.document | filters.video))
async def handle_file(client, message: Message):
    try:
        # Notify the user that the file is being downloaded
        status = await message.reply_text("Downloading the file...")

        # Download the file
        file_path = await client.download_media(message)
        if not file_path:
            await status.edit_text("Failed to download the file.")
            return

        await status.edit_text("File downloaded! Generating link...")

        # Send the file to the file store channel
        sent_message = await app.send_document(
            chat_id=FILE_STORE_CHANNEL,
            document=file_path,
            caption=f"File: `{os.path.basename(file_path)}`",
        )
        
        # Generate a direct download link
        file_id = sent_message.document.file_id
        file_link = f"https://t.me/Rghkklljhhh_bot?start=file_{file_id}"

        # Notify the user and provide the link
        await message.reply_text(
            f"Your file has been uploaded!\n\n📥 **Download Link:** [Click Here]({file_link})",
            disable_web_page_preview=True
        )

        # Clean up the downloaded file
        os.remove(file_path)
        await status.delete()

    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")


@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    # Check if a file ID is provided in the start command
    if len(message.command) > 1:
        file_id = message.command[1]  # Extract the file ID from the start command
        try:
            # Retrieve the file from the file store channel
            await message.reply_document(
                document=file_id,
                caption="Here is your requested file!"
            )
        except Exception as e:
            await message.reply_text(f"An error occurred: {str(e)}")
    else:
        await message.reply_text("Welcome! Send me a file, and I'll generate a direct download link for you.")


if __name__ == "__main__":
    app.run()
