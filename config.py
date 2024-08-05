# config.py

import os

API_ID = os.getenv("API_ID", "21740783")
API_HASH = os.getenv("API_HASH", "a5dc7fec8302615f5b441ec5e238cd46")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7116266807:AAFiuS4MxcubBiHRyzKEDnmYPCRiS0f3aGU")
DOWNLOAD_DIR = "downloads"

# FFmpeg path (if it's not in your PATH, specify it here)
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Adjust based on your system
