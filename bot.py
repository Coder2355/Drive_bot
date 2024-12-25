import base64
from pyrogram import Client, filters
from pyrogram.types import Message
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL




app = Client("fileSendBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)


def encode_file_link(channel_id: int, message_id: int) -> str:
    """Encode the file link into a Base64 string."""
    data = f"{channel_id}:{message_id}"
    return base64.urlsafe_b64encode(data.encode()).decode()


def decode_file_link(encoded_data: str) -> tuple:
    """Decode the Base64 string back into channel_id and message_id."""
    data = base64.urlsafe_b64decode(encoded_data.encode()).decode()
    return tuple(map(int, data.split(":")))


@app.on_message(filters.private & filters.document)
async def handle_file(client: Client, message: Message):
    try:
        # Notify the user
        await message.reply_text("Processing your file...")

        # Forward the file to the file store channel
        forwarded_msg = await message.forward(FILE_STORE_CHANNEL)

        # Use the correct attribute for message ID
        encoded_link = encode_file_link(forwarded_msg.chat.id, forwarded_msg.id)

        # Get bot's username for generating the link
        bot_username = (await client.get_me()).username
        file_link = f"https://t.me/{bot_username}?start={encoded_link}"

        # Send the link back to the user
        await message.reply_text(f"Your file has been uploaded. Here is your link:\n\n{file_link}")
    
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")


@app.on_message(filters.private & filters.command("start"))
async def start(client: Client, message: Message):
    if len(message.command) > 1:
        # Handle the start parameter (decoded Base64)
        encoded_data = message.command[1]
        try:
            channel_id, message_id = decode_file_link(encoded_data)

            # Fetch the file from the file store channel
            file_msg = await client.get_messages(channel_id, message_id)
            await file_msg.copy(message.chat.id)  # Send the file to the user
        except Exception as e:
            await message.reply_text(f"Invalid link or error: {str(e)}")
    else:
        await message.reply_text(
            "Hello! Send me any file, and I'll generate a sharable link for you. 🚀\n\n"
            "If you have a link, click it to retrieve the file!"
        )


if __name__ == "__main__":
    print("Bot is running...")
    app.run()
