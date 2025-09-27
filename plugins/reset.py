
import asyncio
import logging
from database import db
from config import Config
from translation import Translation
from .fsub import send_force_subscribe_message
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Setup logging
logger = logging.getLogger(__name__)


# /reset command removed - now handled by python-telegram-bot in ptb_commands.py

# /resetall command removed - now handled by python-telegram-bot in ptb_commands.py

# Callback handlers for reset confirmations
@Client.on_callback_query(filters.regex(r'^confirm_reset_'))
async def confirm_reset_callback(client, callback_query):
    user_id = callback_query.from_user.id
    target_user_id = int(callback_query.data.split('_')[2])
    
    # Ensure only the user themselves can confirm their reset
    if user_id != target_user_id:
        return await callback_query.answer("❌ You can only reset your own data!", show_alert=True)
    
    try:
        status_msg = await callback_query.message.edit_text(
            "🔄 <b>Resetting your data...</b>\n\n⏳ Please wait..."
        )
        
        # Reset user configurations
        default_config = {
            'caption': None,
            'button': None,
            'duplicate': True,
            'db_uri': None,
            'forward_tag': False,
            'file_size': 0,
            'size_limit': None,
            'extension': None,
            'keywords': None,
            'ftm_mode': False,
            'protect': None,
            'filters': {
                'text': True,
                'photo': True, 
                'video': True,
                'document': True,
                'audio': True,
                'voice': True,
                'animation': True,
                'sticker': True,
                'poll': True,
                'image_text': False
            },
        }
        
        # Update user configs
        await db.update_configs(user_id, default_config)
        
        # Remove all user's bots if exists
        try:
            await db.remove_bot(user_id)
        except Exception as e:
            logger.error(f"Error removing bot for user {user_id}: {e}")
        
        # Get and remove all user's channels
        try:
            user_channels = await db.get_user_channels(user_id)
            for channel in user_channels:
                await db.remove_channel(user_id, channel['chat_id'])
        except Exception as e:
            logger.error(f"Error removing channels for user {user_id}: {e}")
            user_channels = []
        
        # Remove from forwarding notifications
        try:
            await db.rmve_frwd(user_id)
        except Exception as e:
            logger.error(f"Error removing from forwarding for user {user_id}: {e}")
        
        # Send notification for user reset
        try:
            from utils.notifications import NotificationManager
            notify = NotificationManager(client)
            await notify.notify_user_action(
                user_id, 
                "User Data Reset", 
                "User performed complete data reset - all configurations cleared"
            )
        except Exception as notify_err:
            logger.error(f"Failed to send reset notification: {notify_err}")
        
        await status_msg.edit_text(
            "✅ <b>Reset Complete!</b>\n\n"
            "<b>Successfully reset:</b>\n"
            f"• User configurations\n"
            f"• Bot connections ({len(user_channels) > 0 and 'removed' or 'none'})\n"
            f"• Channel settings ({len(user_channels)} channels removed)\n"
            "• All custom settings\n\n"
            "<b>Your account has been restored to default settings.</b>\n"
            "<b>You can now reconfigure everything from scratch.</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🏠 Back to Main Menu', callback_data='back')
            ]])
        )
        
        logger.info(f"User {user_id} successfully reset their data")
        
    except Exception as e:
        logger.error(f"Error in confirm_reset for user {user_id}: {e}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ <b>Reset Failed!</b>\n\n"
            "An error occurred while resetting your data.\n"
            "Please try again or contact admin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔄 Try Again', callback_data=f'confirm_reset_{user_id}'),
                InlineKeyboardButton('🏠 Main Menu', callback_data='back')
            ]])
        )

@Client.on_callback_query(filters.regex(r'^confirm_resetall$'))
async def confirm_resetall_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    # Double check admin permissions
    if user_id not in Config.OWNER_ID:
        return await callback_query.answer("❌ Only owners can perform this action!", show_alert=True)
    
    try:
        status_msg = await callback_query.message.edit_text(
            "🔄 <b>ADMIN RESET ALL IN PROGRESS...</b>\n\n"
            "⏳ <b>Processing all users...</b>\n"
            "📊 <b>Progress:</b> Starting...\n\n"
            "<i>This may take several minutes for large databases.</i>"
        )
        
        # Get all users
        users = await db.get_all_users()
        
        # Reset counters
        total = success = failed = bots_removed = channels_removed = 0
        
        # Default configuration
        default_config = {
            'caption': None,
            'button': None,
            'duplicate': True,
            'db_uri': None,
            'forward_tag': False,
            'file_size': 0,
            'size_limit': None,
            'extension': None,
            'keywords': None,
            'ftm_mode': False,
            'protect': None,
            'filters': {
                'text': True,
                'photo': True, 
                'video': True,
                'document': True,
                'audio': True,
                'voice': True,
                'animation': True,
                'sticker': True,
                'poll': True,
                'image_text': False
            },
        }
        
        async for user in users:
            target_user_id = user['id']
            total += 1
            
            # Update progress every 10 users
            if total % 10 == 0:
                await status_msg.edit_text(
                    "🔄 <b>ADMIN RESET ALL IN PROGRESS...</b>\n\n"
                    f"📊 <b>Progress:</b> {total} users processed\n"
                    f"✅ <b>Success:</b> {success}\n"
                    f"❌ <b>Failed:</b> {failed}\n"
                    f"🤖 <b>Bots Removed:</b> {bots_removed}\n"
                    f"📺 <b>Channels Removed:</b> {channels_removed}\n\n"
                    "<i>Please wait...</i>"
                )
            
            try:
                # Reset user configs
                await db.update_configs(target_user_id, default_config)
                
                # Remove user's bot if exists
                try:
                    bot_exists = await db.is_bot_exist(target_user_id)
                    if bot_exists:
                        await db.remove_bot(target_user_id)
                        bots_removed += 1
                except Exception as bot_err:
                    logger.error(f"Error removing bot for user {target_user_id}: {bot_err}")
                
                # Remove all user's channels
                try:
                    user_channels = await db.get_user_channels(target_user_id)
                    for channel in user_channels:
                        await db.remove_channel(target_user_id, channel['chat_id'])
                        channels_removed += 1
                except Exception as channel_err:
                    logger.error(f"Error removing channels for user {target_user_id}: {channel_err}")
                
                # Remove from forwarding notifications
                try:
                    await db.rmve_frwd(target_user_id)
                except Exception as frwd_err:
                    logger.error(f"Error removing from forwarding for user {target_user_id}: {frwd_err}")
                
                success += 1
                
            except Exception as e:
                logger.error(f"Failed to reset user {target_user_id}: {e}")
                failed += 1
        
        # Send admin notification
        try:
            from utils.notifications import NotificationManager
            notify = NotificationManager(client)
            await notify.notify_admin_action(
                user_id,
                "Mass User Reset",
                f"Admin performed complete reset of all {total} users",
                details=f"Success: {success}, Failed: {failed}, Bots removed: {bots_removed}, Channels removed: {channels_removed}"
            )
        except Exception as notify_err:
            logger.error(f"Failed to send admin reset notification: {notify_err}")
        
        # Final status message
        await status_msg.edit_text(
            "✅ <b>ADMIN RESET ALL COMPLETED!</b>\n\n"
            f"📊 <b>Final Statistics:</b>\n"
            f"👥 <b>Total Users:</b> {total}\n"
            f"✅ <b>Successfully Reset:</b> {success}\n"
            f"❌ <b>Failed:</b> {failed}\n"
            f"🤖 <b>Bots Removed:</b> {bots_removed}\n"
            f"📺 <b>Channels Removed:</b> {channels_removed}\n\n"
            f"<b>✨ All user data has been reset to default settings!</b>\n"
            f"<b>🔄 Database cleanup completed successfully.</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🏠 Back to Admin Panel', callback_data='admin_commands')
            ]])
        )
        
        logger.info(f"Admin {user_id} completed resetall - Total: {total}, Success: {success}, Failed: {failed}")
        
    except Exception as e:
        logger.error(f"Error in confirm_resetall for admin {user_id}: {e}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ <b>RESET ALL FAILED!</b>\n\n"
            "A critical error occurred during the mass reset.\n"
            "Some users may have been partially reset.\n\n"
            "<b>Please check logs and try again if needed.</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔄 Try Again', callback_data='confirm_resetall'),
                InlineKeyboardButton('🏠 Admin Panel', callback_data='admin_commands')
            ]])
        )

@Client.on_callback_query(filters.regex(r'^cancel_reset$'))
async def cancel_reset_callback(client, callback_query):
    await callback_query.message.edit_text(
        "❌ <b>Reset Cancelled</b>\n\n"
        "Your data remains unchanged.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('🏠 Back to Main Menu', callback_data='back')
        ]])
    )

@Client.on_callback_query(filters.regex(r'^cancel_resetall$'))
async def cancel_resetall_callback(client, callback_query):
    await callback_query.message.edit_text(
        "❌ <b>Reset All Cancelled</b>\n\n"
        "No user data was modified.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('🏠 Back to Admin Panel', callback_data='admin_commands')
        ]])
    )
