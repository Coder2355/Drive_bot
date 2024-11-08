from pyrogram import Client, filters
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

app = Client(
    "gplink_unshortener_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

def unshorten_gplink(url):
    # Setup Selenium options for headless mode
    options = Options()
    options.add_argument("--headless")  # Run without GUI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # Disables GPU rendering
    options.add_argument("--disable-software-rasterizer")  # Required for headless servers

    try:
        # Use Service object for ChromeDriver
        driver_service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=driver_service, options=options)  # Corrected initialization
        driver.get(url)

        # Wait through the timer (adjust as needed)
        time.sleep(15)

        # Get final redirected URL
        expanded_url = driver.current_url
        driver.quit()
        return expanded_url
    except Exception as e:
        print(f"Error: {e}")
        if 'driver' in locals():
            driver.quit()
        return None

@app.on_message(filters.command("unshort") & filters.private)
async def unshort_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text("Please provide a GPLinks URL to unshorten.\nUsage: /unshort <gplink>")
        return

    url = message.command[1]
    if "gplinks" not in url:
        await message.reply_text("Please provide a valid GPLinks URL.")
        return

    await message.reply_text("🔍 Unshortening your GPLinks URL...")

    # Process URL
    expanded_url = unshorten_gplink(url)

    if expanded_url:
        await message.reply_text(f"🔗 Original URL:\n{expanded_url}")
    else:
        await message.reply_text("❗ Couldn't unshorten the URL. Please try again.")

if __name__ == "__main__":
    app.run()
