# config.py

import os

  
API_ID = os.getenv("API_ID", "21740783")
API_HASH = os.getenv("API_HASH", "a5dc7fec8302615f5b441ec5e238cd46")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7766709030:AAEHnIF6EkNttAij4cOCZat74PMK5Ymm6is")
PORT = int(os.getenv("PORT", 8000))
DOWNLOAD_DIR = "downloads/"
SOURCE_CHANNEL_ID = "-1002183423252"

