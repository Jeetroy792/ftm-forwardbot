import asyncio
import logging 
import os
import logging.config
from database import db 
from config import Config  
from pyrogram import Client, __version__

# Validate environment variables before starting
Config.validate_env()
from pyrogram.raw.all import layer 
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram import utils as pyroutils 

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# Adjust Pyrogram chat ID ranges to solve peer ID issue
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

class Bot(Client): 
    def __init__(self):
        super().__init__(
            Config.BOT_SESSION,
            api_hash=Config.API_HASH,
            api_id=Config.API_ID,
            plugins={
                "root": "plugins"
            },
            workers=50,
            bot_token=Config.BOT_TOKEN
        )
        self.log = logging
        self.log_channel_id = getattr(Config, 'LOG_CHANNEL_ID', -1003003594014)  # Default to the mentioned channel
        self.notification_manager = None  # Will be initialized after start

    async def start(self):
        await super().start()
        me = await self.get_me()
        logging.info(f"{me.first_name} with for pyrogram v{__version__} (Layer {layer}) started on @{me.username}.")
        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        self.set_parse_mode(ParseMode.DEFAULT)
        
        # Initialize notification manager
        from utils.notifications import NotificationManager
        self.notification_manager = NotificationManager(self)
        
        
        
        text = "**๏[-ิ_•ิ]๏ bot restarted !**"
        logging.info(text)
        success = failed = 0
        
        # Send restart message to all users (not just forwarding users)
        all_users = await db.get_all_users()
        for user in all_users:
           chat_id = user['id']
           try:
              await self.send_message(chat_id, text)
              success += 1
           except FloodWait as e:
              await asyncio.sleep(e.value + 1)
              try:
                 await self.send_message(chat_id, text)
                 success += 1
              except Exception:
                 failed += 1
           except Exception:
              failed += 1 
        
        # Also send to owner
        for owner_id in Config.OWNER_ID:
           try:
              await self.send_message(owner_id, text)
           except Exception:
              pass
        
        # Clear all forwarding sessions
        await db.rmve_frwd(all=True)
        if (success + failed) != 0:
           logging.info(f"Restart message status - "
                 f"success: {success}, "
                 f"failed: {failed}")
        
        # Grant lifetime Pro subscriptions to all sudo users if not already given
        await self.grant_sudo_lifetime_subscriptions()
        
        # Send startup notification to log channel after restart messages are sent
        try:
            startup_msg = f"""<b>🚀 Bot Started Successfully!</b>

<b>Bot Name:</b> {me.first_name}
<b>Username:</b> @{me.username}
<b>Bot ID:</b> <code>{me.id}</code>
<b>Pyrogram Version:</b> v{__version__}
<b>Layer:</b> {layer}

<b>Restart Stats:</b>
• Success: {success} users notified
• Failed: {failed} users failed
• Total Users: {success + failed}

<b>Status:</b> ✅ Online and Ready"""
            
            await self.notification_manager.send_log_notification(startup_msg)
            logging.info("Startup notification sent to log channel")
        except Exception as e:
            logging.error(f"Failed to send startup notification: {e}")
        
        # Start background cleanup task for chat requests
        try:
            from utils.cleanup import periodic_cleanup
            asyncio.create_task(periodic_cleanup())
            logging.info("Background cleanup task started")
        except Exception as e:
            logging.error(f"Failed to start cleanup task: {e}")

    async def grant_sudo_lifetime_subscriptions(self):
        """Grant lifetime Pro subscriptions to all sudo users if not already given"""
        try:
            # Get all sudo users (owners + admins)
            sudo_users = Config.OWNER_ID + Config.ADMIN_ID
            granted_count = 0
            
            for sudo_user_id in sudo_users:
                try:
                    # Check if user already has an active premium subscription
                    existing_premium = await db.get_premium_user_details(sudo_user_id)
                    
                    if existing_premium and existing_premium.get('is_active', False):
                        # Check if it's already a lifetime subscription
                        if existing_premium.get('amount_paid') == 'sudo_lifetime_subscription':
                            logging.info(f"Sudo user {sudo_user_id} already has lifetime subscription, skipping")
                            continue
                        else:
                            # User has some other subscription, remove it first
                            await db.remove_premium_user(sudo_user_id)
                            logging.info(f"Removed existing subscription for sudo user {sudo_user_id}")
                    
                    # Grant lifetime Pro subscription (999 years)
                    await db.add_premium_user(
                        user_id=sudo_user_id,
                        plan_type="pro",
                        duration_days=365250,  # 999+ years (lifetime)
                        amount_paid="sudo_lifetime_subscription"
                    )
                    
                    granted_count += 1
                    logging.info(f"✅ Granted lifetime Pro subscription to sudo user {sudo_user_id}")
                    
                    # Send notification to the sudo user
                    try:
                        await self.send_message(
                            sudo_user_id,
                            "<b>🎉 Lifetime Pro Access Granted!</b>\n\n"
                            "<b>✅ You have been automatically granted lifetime Pro access as a sudo user!</b>\n\n"
                            "<b>🏆 Pro Plan Benefits:</b>\n"
                            "• ♾️ Unlimited forwarding processes\n"
                            "• 🔥 FTM mode with source tracking\n"
                            "• 🛡️ Priority support\n"
                            "• ⚡ Enhanced performance\n"
                            "• 📈 All premium features unlocked\n\n"
                            "<b>⏰ Duration:</b> Lifetime (999+ years)\n"
                            "<b>🔑 Access Level:</b> Sudo User\n\n"
                            "<b>Use /myplan to check your subscription details.</b>"
                        )
                    except Exception as notify_error:
                        logging.error(f"Failed to notify sudo user {sudo_user_id}: {notify_error}")
                        
                except Exception as user_error:
                    logging.error(f"Failed to grant subscription to sudo user {sudo_user_id}: {user_error}")
                    
            if granted_count > 0:
                logging.info(f"✅ Granted lifetime Pro subscriptions to {granted_count} sudo users")
                
                # Send notification to log channel
                try:
                    await self.notification_manager.send_log_notification(
                        f"<b>🏆 Sudo Lifetime Subscriptions Granted!</b>\n\n"
                        f"<b>Count:</b> {granted_count} users\n"
                        f"<b>Plan:</b> Pro (Lifetime)\n"
                        f"<b>Access Level:</b> Sudo Users\n"
                        f"<b>Duration:</b> 999+ years\n\n"
                        f"<b>✅ All sudo users now have lifetime Pro access!</b>"
                    )
                except Exception as log_error:
                    logging.error(f"Failed to send sudo subscription log: {log_error}")
            else:
                logging.info("ℹ️ No new sudo lifetime subscriptions needed - all already have access")
                
        except Exception as e:
            logging.error(f"Error granting sudo lifetime subscriptions: {e}")

    async def stop(self, *args):
        msg = f"@{self.username} stopped. Bye."
        await super().stop()
        logging.info(msg)

if __name__ == "__main__":
    bot = Bot()
    bot.run()
