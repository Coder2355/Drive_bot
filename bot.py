from pyrogram import Client, filters
import requests
import config
import time

app = Client(
    "gplink_unshortener_bot",
    api_id=config.api_id,
    api_hash=config.api_hash,
    bot_token=config.bot_token
)

def unshorten_gplink(url):
    try:
        # Start a session to handle cookies and headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://gplinks.in'
        })
        
        # Initial request
        response = session.get(url)
        
        # Follow redirects and intermediate steps if needed
        while 'gplinks' in response.url:
            time.sleep(2)  # Bypass time delay
            response = session.get(response.url)

        # Final expanded URL
        return response.url
    except Exception as e:
        print(f"Error during unshortening: {e}")
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
