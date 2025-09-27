import os
import asyncio
import threading
from flask import Flask
from bot import Bot
from ptb_commands import setup_ptb_application

# Create Flask app for Render/uptime monitoring
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Fᴛᴍ Dᴇᴠᴇʟᴏᴘᴇʀᴢ bot is live with hybrid PTB support."

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# Run Flask in background
threading.Thread(target=run_flask).start()

async def run_pyrogram_bot():
    """Run the Pyrogram bot"""
    print("Starting Pyrogram bot...")
    app = Bot()
    await app.start()
    await asyncio.Event().wait()  # Keep running forever

async def run_ptb_bot():
    """Run the python-telegram-bot for specific commands"""
    print("Starting Python-Telegram-Bot for specific commands...")
    application = setup_ptb_application()
    await application.initialize()
    await application.start()
    
    # Only handle messages, let Pyrogram handle callback queries
    await application.updater.start_polling(allowed_updates=["message"])
    
    # Keep running
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# Your async main - runs both bots concurrently
async def main():
    """Run both Pyrogram and Python-Telegram-Bot concurrently"""
    try:
        # Run both bots concurrently
        await asyncio.gather(
            run_pyrogram_bot(),
            run_ptb_bot()
        )
    except Exception as e:
        print(f"Error running bots: {e}")

# Safe async run
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        print(f"[!] RuntimeError: {e}")
        loop = asyncio.get_event_loop()
        
        # Create tasks for both bots
        loop.create_task(run_pyrogram_bot())
        loop.create_task(run_ptb_bot())
        
        loop.run_forever()
