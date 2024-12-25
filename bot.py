import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL

# Initialize SQLite database
conn = sqlite3.connect("files.db")
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT NOT NULL,
        file_name TEXT NOT NULL
    )
    """
)
conn.commit()

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

        await status.edit_text("File downloaded! Uploading to the file store...")

        # Send the file to the file store channel
        sent_message = await app.send_document(
            chat_id=FILE_STORE_CHANNEL,
            document=file_path,
            caption=f"File: `{os.path.basename(file_path)}`",
        )
        
        # Save file metadata in the database
        file_id = sent_message.document.file_id
        file_name = os.path.basename(file_path)
        cursor.execute("INSERT INTO files (file_id, file_name) VALUES (?, ?)", (file_id, file_name))
        conn.commit()

        # Generate a link with the database ID
        file_db_id = cursor.lastrowid
        file_link = f"https://t.me/Rghkklljhhh_bot?start=file_{file_db_id}"

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
        file_db_id = message.command[1].replace("file_", "")  # Extract database ID
        try:
            # Retrieve file metadata from the database
            cursor.execute("SELECT file_id, file_name FROM files WHERE id = ?", (file_db_id,))
            file_data = cursor.fetchone()

            if file_data:
                file_id, file_name = file_data

                # Send the file back to the user
                await message.reply_document(
                    document=file_id,
                    caption=f"Here is your requested file: `{file_name}`",
                )
            else:
                await message.reply_text("File not found in the database.")

        except Exception as e:
            await message.reply_text(f"Failed to retrieve the file. Error: {str(e)}")
    else:
        await message.reply_text("Welcome! Send me a file, and I'll generate a direct download link for you.")


if __name__ == "__main__":
    app.run()
