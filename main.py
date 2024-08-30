from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

audio_feature_buttons = InlineKeyboardMarkup(
    [        
        [InlineKeyboardButton("Audio Trimmer✂️", callback_data="handle_trim_audio"),
         InlineKeyboardButton("Audio+Audio🎵", callback_data="set_merge_audio")],
        [InlineKeyboardButton("Audio Compress 🗜️", callback_data="compress_audio")],
        [InlineKeyboardButton("Cancel❌", callback_data="close")]
    ]
)

@app.on_message(filters.audio)
async def handle_audio_file(client, message):
    await message.reply_text(
        "What do you want me to do with this audio file?",
        reply_markup=audio_feature_buttons,
        quote=True  # Force reply
    )
