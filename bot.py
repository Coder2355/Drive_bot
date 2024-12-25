import base64
import re
from pyrogram import Client, filters
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999
from config import API_ID, API_HASH, BOT_TOKEN, FILE_STORE_CHANNEL, TARGET_CHANNEL


from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


app = Client("animeUploadBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Data to store posters and quality-based links
posters = {}  # {user_id: poster_file_id}
posts = {}  # {(anime_name, episode_number): target_message_id}


def encode_file_link(channel_id: int, message_id: int) -> str:
    """Encode the file link into a Base64 string."""
    data = f"{channel_id}:{message_id}"
    return base64.urlsafe_b64encode(data.encode()).decode()


def decode_file_link(encoded_data: str) -> tuple:
    """Decode the Base64 string back into channel_id and message_id."""
    data = base64.urlsafe_b64decode(encoded_data.encode()).decode()
    return tuple(map(int, data.split(":")))


def extract_file_details(file_name: str):
    """Extract anime name, episode number, and quality from the file name."""
    match = re.match(r"(.+)\s[Ee]p?\s?(\d+).*(\d{3,4}p)", file_name)
    if match:
        anime_name = match.group(1).strip()
        episode_number = int(match.group(2))
        quality = match.group(3)
        return anime_name, episode_number, quality
    return None, None, None


@app.on_message(filters.private & filters.photo)
async def set_poster(client: Client, message: Message):
    """Set poster for the anime."""
    posters[message.from_user.id] = message.photo.file_id
    await message.reply_text("Poster added successfully ✅")


@app.on_message(filters.private & (filters.document | filters.video))
async def handle_file(client: Client, message: Message):
    """Handle video or document files."""
    if message.from_user.id not in posters:
        await message.reply_text("Please send a poster first.")
        return

    # Extract details from the filename
    file_name = message.document.file_name if message.document else message.video.file_name
    anime_name, episode_number, quality = extract_file_details(file_name)

    if not all([anime_name, episode_number, quality]):
        await message.reply_text("Could not extract details. Ensure the filename contains 'Anime Name Ep X Quality'.")
        return

    await message.reply_text("Processing your file...")

    # Forward the file to the file store channel
    forwarded_msg = await message.forward(FILE_STORE_CHANNEL)
    encoded_link = encode_file_link(forwarded_msg.chat.id, forwarded_msg.id)
    bot_username = (await client.get_me()).username
    download_link = f"https://t.me/{bot_username}?start={encoded_link}"

    # Create or update the post in the target channel
    post_key = (anime_name, episode_number)
    quality_button = InlineKeyboardButton(quality, url=download_link)

    if post_key not in posts:
        # Create a new post
        poster_id = posters[message.from_user.id]
        caption = f"**{anime_name}**\nEpisode: {episode_number}\n\nSelect quality below:"
        buttons = [[quality_button]]

        target_message = await client.send_photo(
            TARGET_CHANNEL,
            photo=poster_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        posts[post_key] = target_message.id
    else:
        # Update the existing post
        target_message = await client.get_messages(TARGET_CHANNEL, posts[post_key])
        existing_buttons = target_message.reply_markup.inline_keyboard
        new_buttons = existing_buttons + [[quality_button]]

        await target_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_buttons))

    # Notify the user
    if len(new_buttons) == 3:
        await message.reply_text("All qualities uploaded successfully ✅")
    else:
        await message.reply_text(f"Uploaded {quality} successfully ✅")


@app.on_message(filters.private & filters.command("start"))
async def start(client: Client, message: Message):
    """Start command handler."""
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
            "Hello! Send me a poster and files to create sharable posts with quality buttons."
        )


if __name__ == "__main__":
    print("Bot is running...")
    app.run()
