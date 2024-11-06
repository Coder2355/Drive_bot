from pyrogram import Client, filters
import config
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

app = Client(
    "gplink_unshortener_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

def unshorten_gplink(url):
    # Setup Selenium options
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver_service = Service('/path/to/chromedriver')  # Specify path if needed

    try:
        # Initialize WebDriver
        driver = webdriver.Chrome(service=driver_service, options=options)
        driver.get(url)

        # Wait through 15-second timer and redirection
        time.sleep(15)  # Wait for the timer (adjust as needed)

        # After waiting, fetch the final redirected URL
        expanded_url = driver.current_url
        driver.quit()
        return expanded_url
    except Exception as e:
        print(f"Error: {e}")
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
