from pyrogram import Client, filters
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

app = Client(
    "gplink_unshortener_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

def unshorten_gplink(url):
    # Setup Chrome options
    options = Options()
    options.binary_location = "/usr/bin/google-chrome"  # Chrome binary location in Colab
    options.add_argument("--headless")  # Enable headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        # Initialize WebDriver with ChromeDriver path
        driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=options)
        driver.get(url)

        # Wait to bypass the timer (adjust the sleep time as needed)
        time.sleep(15)

        # Get the final URL after redirection
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
