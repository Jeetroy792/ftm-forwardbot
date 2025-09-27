import os
import sys
import asyncio
import logging
import psutil
import speedtest
import platform
import subprocess
from datetime import datetime
from database import db, mongodb_version
from config import Config, temp
from platform import python_version
from translation import Translation
from utils.notifications import NotificationManager
from .fsub import send_force_subscribe_message, get_force_sub_buttons, build_force_subscribe_message_and_buttons
from plugins.timezone import get_current_ist_timestamp
from pyrogram import Client, filters, enums, __version__ as pyrogram_version
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument

# Setup logging
logger = logging.getLogger(__name__)

def get_main_buttons():
    """Dynamically generate the main buttons for the bot's menu."""
    return [[
        InlineKeyboardButton('📜 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ ', url=Config.SUPPORT_GROUP),
        InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ  ', url=Config.UPDATE_CHANNEL)
        ],[
        InlineKeyboardButton('🎁 Get Free Trial', callback_data='get_free_trial'),
        InlineKeyboardButton('📊 My Plan', callback_data='my_plan')
        ],[
        InlineKeyboardButton('💎 Premium Plans', callback_data='premium_plans'),
        InlineKeyboardButton('🙋‍♂️ ʜᴇʟᴘ', callback_data='help')
        ],[
        InlineKeyboardButton('💁‍♂️ ᴀʙᴏᴜᴛ ', callback_data='about'),
        InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ⚙️', callback_data='settings#main')
        ],[
        InlineKeyboardButton('📞 Contact Admin', callback_data='contact_admin')
        ]]


#===================Start Function===================#

@Client.on_message(filters.private & filters.command(['trial']))
async def trial_command(client, message):
    """Handle trial command"""
    user_id = message.from_user.id
    logger.info(f"Trial command from user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id) and Config.MULTI_FSUB:
            subscription_status = await db.check_force_subscribe(user_id, client)
            if not subscription_status['all_subscribed']:
                force_buttons, joined_channels = await get_force_sub_buttons(client, user_id)
                if force_buttons:
                    force_sub_text = Translation.FORCE_SUBSCRIBE_MSG
                    if joined_channels:
                        force_sub_text += f"\n\n<b>✅ Already Joined:</b>\n"
                        for channel in joined_channels:
                            force_sub_text += f"• {channel} ✅\n"
                        force_sub_text += f"\n<b>📢 Please join the remaining channels below:</b>"

                    return await message.reply_text(
                        text=force_sub_text,
                        reply_markup=InlineKeyboardMarkup(force_buttons),
                        quote=True
                    )

        # Check if user can use trial
        can_trial = await db.can_use_trial(user_id)

        if not can_trial:
            await message.reply_text(
                text="<b>❌ Trial Already Used!</b>\n\n"
                     "<b>You have already used your free trial this year.</b>\n"
                     "<b>Trial is available once per calendar year.</b>\n\n"
                     "<b>💎 Check our premium plans with /plan</b>",
                quote=True
            )
            return

        # Check if user already has premium
        is_premium = await db.is_premium_user(user_id)
        if is_premium:
            await message.reply_text(
                text="<b>✅ You already have premium access!</b>\n\n"
                     "<b>Use /myplan to check your subscription details.</b>",
                quote=True
            )
            return

        # Grant trial
        success, result = await db.grant_trial(user_id)

        if success:
            from plugins.timezone import display_expiry_date
            expires_date = display_expiry_date(result)
            await message.reply_text(
                text=f"<b>🎉 3-Day Trial Activated!</b>\n\n"
                     f"<b>✅ You now have unlimited forwarding for 3 days!</b>\n\n"
                     f"<b>Trial Benefits:</b>\n"
                     f"• ✅ Unlimited forwarding processes\n"
                     f"• ✅ All premium features (except FTM mode)\n"
                     f"• ✅ Priority support\n\n"
                     f"<b>⏰ Expires:</b> {expires_date}\n\n"
                     f"<b>💡 Use /forward to start forwarding messages!</b>\n"
                     f"<b>📊 Check status anytime with /myplan</b>",
                quote=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('📊 My Plan', callback_data='my_plan'),
                    InlineKeyboardButton('🚀 Start Forwarding', callback_data='start_forwarding')
                ]])
            )

            # Send notification
            notify = NotificationManager(client)
            await notify.notify_user_action(
                user_id,
                "Trial Activated",
                f"User activated 3-day free trial - expires {expires_date}"
            )

        else:
            await message.reply_text(
                text=f"<b>❌ Trial Activation Failed</b>\n\n"
                     f"<b>Reason:</b> {result}\n\n"
                     f"<b>💎 Check our premium plans with /plan</b>",
                quote=True
            )

    except Exception as e:
        logger.error(f"Error in trial command for user {user_id}: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred. Please try again.", quote=True)

@Client.on_message(filters.private & filters.command(['commands']))
async def commands_list(client, message):
    """Show all available commands"""
    user_id = message.from_user.id
    logger.info(f"Commands list requested by user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id) and Config.MULTI_FSUB:
            subscription_status = await db.check_force_subscribe(user_id, client)
            if not subscription_status['all_subscribed']:
                force_buttons, joined_channels = await get_force_sub_buttons(client, user_id)
                if force_buttons:
                    force_sub_text = Translation.FORCE_SUBSCRIBE_MSG
                    if joined_channels:
                        force_sub_text += f"\n\n<b>✅ Already Joined:</b>\n"
                        for channel in joined_channels:
                            force_sub_text += f"• {channel} ✅\n"
                        force_sub_text += f"\n<b>📢 Please join the remaining channels below:</b>"

                    return await message.reply_text(
                        text=force_sub_text,
                        reply_markup=InlineKeyboardMarkup(force_buttons),
                        quote=True
                    )

        is_admin = Config.is_sudo_user(user_id)
        is_premium = await db.is_premium_user(user_id)
        can_trial = await db.can_use_trial(user_id)

        commands_text = "<b>📋 Available Commands</b>\n\n"

        commands_text += "<b>🔥 Essential Commands:</b>\n"
        commands_text += "• <code>/start</code> - Start bot and show main menu\n"
        commands_text += "• <code>/help</code> - Get detailed help and instructions\n"
        commands_text += "• <code>/forward</code> - Start message forwarding process\n"
        commands_text += "• <code>/settings</code> - Configure your bot settings\n"
        commands_text += "• <code>/myplan</code> - Check your subscription status\n"
        commands_text += "• <code>/info</code> - Get your account information\n"
        commands_text += "• <code>/reset</code> - Reset your bot configurations\n\n"

        commands_text += "<b>💎 Premium Features:</b>\n"
        if not is_premium and can_trial:
            commands_text += "• <code>/trial</code> - Get 3-day free trial (⭐ Available!)\n"
        elif not is_premium:
            commands_text += "• <code>/trial</code> - Get 3-day free trial (❌ Used this year)\n"
        else:
            commands_text += "• <code>/trial</code> - Get 3-day free trial (✅ You have premium)\n"

        commands_text += "• <code>/verify</code> - Verify payment for premium plans\n"
        commands_text += "• <code>/plan</code> - View available premium plans\n\n"

        if is_admin:
            commands_text += "<b>👑 Admin Commands:</b>\n"
            commands_text += "• <code>/users</code> - List all registered users\n"
            commands_text += "• <code>/broadcast</code> - Send message to all users\n"
            commands_text += "• <code>/speedtest</code> - Network speed test\n"
            commands_text += "• <code>/system</code> - System information\n"
            commands_text += "• <code>/resetall</code> - Reset all users (DANGER)\n"
            commands_text += "• <code>/premium add</code> - Grant premium to user\n"
            commands_text += "• <code>/premium remove</code> - Remove premium from user\n\n"

        commands_text += "<b>🎯 Quick Status:</b>\n"
        commands_text += f"• <b>Plan:</b> {'Premium' if is_premium else 'Free'}\n"
        commands_text += f"• <b>Trial:</b> {'Available' if can_trial and not is_premium else 'Used/Premium'}\n"
        commands_text += f"• <b>Admin:</b> {'Yes' if is_admin else 'No'}\n\n"

        commands_text += "<b>💡 Pro Tip:</b> Use /trial for instant premium access!"

        await message.reply_text(
            text=commands_text,
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton('🎁 Free Trial', callback_data='get_free_trial'),
                    InlineKeyboardButton('📊 My Plan', callback_data='my_plan')
                ],
                [
                    InlineKeyboardButton('💎 Premium Plans', callback_data='premium_plans'),
                    InlineKeyboardButton('📋 Help', callback_data='help')
                ],
                [
                    InlineKeyboardButton('🏠 Main Menu', callback_data='back')
                ]
            ])
        )

    except Exception as e:
        logger.error(f"Error in commands list for user {user_id}: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred. Please try again.", quote=True)

@Client.on_message(filters.private & filters.command(['start']))
async def start(client, message):
    user = message.from_user
    logger.info(f"Start command from user {user.id} ({user.first_name})")

    try:
        # Check if user came through referral link
        referral_code = None
        if len(message.command) > 1:
            potential_referral = message.command[1]
            # Check if it's a valid referral code (starts with ftmbotzx, accepts both 12 and 13 chars for legacy support)
            if potential_referral.startswith('ftmbotzx') and len(potential_referral) in [12, 13]:
                referral_code = potential_referral
                logger.info(f"User {user.id} joined through referral code: {referral_code}")

        is_new_user = False
        if not await db.is_user_exist(user.id):
            await db.add_user(user.id, user.first_name)
            logger.info(f"New user added: {user.id}")
            is_new_user = True

            # Notify about new user
            notify = NotificationManager(client)
            await notify.notify_user_action(user.id, "New User Registration", f"User: {user.first_name}")
            
        # Handle referral tracking for users with referral code
        if referral_code:
            logger.info(f"Processing referral code {referral_code} for user {user.id} (new_user: {is_new_user})")
            
            # Only set up referral for new users or existing users without referral
            user_data = await db.get_user(user.id)
            
            if not user_data or not user_data.get('referred_by'):
                try:
                    # Check if referring user exists
                    referring_user = await db.get_user_by_referral_code(referral_code)
                    if referring_user:
                        # Set up referral tracking
                        referral_success = await db.set_user_referred_by(user.id, referral_code)
                        if referral_success:
                            logger.info(f"✅ Referral tracking successfully set up for user {user.id} via {referral_code}")
                            
                            # Mark referral bot started
                            await db.mark_referral_bot_started(user.id)
                            logger.info(f"Marked referral bot started for user {user.id}")

                            # Send referral tracking notification immediately
                            try:
                                from .fsub import _send_referral_tracking_notification
                                await _send_referral_tracking_notification(client, referring_user['id'], user.id)
                                logger.info(f"Sent referral tracking notification for user {user.id}")
                            except Exception as e:
                                logger.error(f"Error sending initial referral tracking notification: {e}")
                        else:
                            logger.error(f"❌ Failed to set referral tracking for user {user.id} via {referral_code}")
                    else:
                        logger.warning(f"❌ No user found with referral code {referral_code} - cannot set up referral for user {user.id}")
                        
                except Exception as referral_error:
                    logger.error(f"Error processing referral for user {user.id}: {referral_error}")
            else:
                logger.info(f"User {user.id} already has referral tracking, skipping")
        else:
            logger.info(f"No referral code provided for user {user.id}")

        # Auto-grant premium to sudo users (owners and admins)
        if Config.is_sudo_user(user.id):
            if not await db.is_premium_user(user.id):
                from datetime import datetime, timedelta
                # Grant unlimited premium to sudo users (expires in 10 years)
                await db.add_premium_user(user.id, "pro", 3650, 0)
                logger.info(f"Auto-granted premium to sudo user: {user.id}")
            
            # Handle referral completion for sudo users who came via referral
            # Since sudo users skip force subscribe, we need to complete their referrals here
            user_data = await db.get_user(user.id)
            if user_data and user_data.get('referred_by') and not user_data.get('referral_completed'):
                logger.info(f"Completing referral for sudo user {user.id}")
                await db.mark_referral_bot_started(user.id)
                referral_result = await db.mark_referral_channels_joined(user.id)
                
                # If referral was completed, send notifications
                if referral_result and isinstance(referral_result, dict) and referral_result.get('completed'):
                    try:
                        from .fsub import _send_referral_completion_notifications
                        await _send_referral_completion_notifications(
                            client, 
                            referral_result['referrer_user_id'], 
                            referral_result['referred_user_id'],
                            referral_result['total_referrals'],
                            referral_result['reward_granted']
                        )
                        logger.info(f"Referral completion notifications sent for sudo user {user.id}")
                    except Exception as e:
                        logger.error(f"Error sending referral completion notifications for sudo user: {e}")

        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user.id) and Config.MULTI_FSUB:
            subscription_status = await db.check_force_subscribe(user.id, client)
            if not subscription_status['all_subscribed']:
                force_buttons, joined_channels = await get_force_sub_buttons(client, user.id)
                if force_buttons:
                    force_sub_text = Translation.FORCE_SUBSCRIBE_MSG
                    if joined_channels:
                        force_sub_text += f"\n\n<b>✅ Already Joined:</b>\n"
                        for channel in joined_channels:
                            force_sub_text += f"• {channel} ✅\n"
                        force_sub_text += f"\n<b>📢 Please join the remaining channels below:</b>"

                    return await message.reply_text(
                        text=force_sub_text,
                        reply_markup=InlineKeyboardMarkup(force_buttons),
                        quote=True
                    )
            else:
                # User is already subscribed to all channels
                # Check if this user was referred and complete the referral if needed
                user_data = await db.get_user(user.id)
                if user_data and user_data.get('referred_by') and not user_data.get('referral_completed'):
                    # Mark bot started and channels joined, then complete referral
                    await db.mark_referral_bot_started(user.id)
                    referral_result = await db.mark_referral_channels_joined(user.id)
                    
                    # If referral was completed, send notifications
                    if referral_result and isinstance(referral_result, dict) and referral_result.get('completed'):
                        try:
                            from .fsub import _send_referral_completion_notifications
                            await _send_referral_completion_notifications(
                                client, 
                                referral_result['referrer_user_id'], 
                                referral_result['referred_user_id'],
                                referral_result['total_referrals'],
                                referral_result['reward_granted']
                            )
                            logger.info(f"Referral completion notifications sent for already subscribed user {user.id}")
                        except Exception as e:
                            logger.error(f"Error sending referral completion notifications for already subscribed user: {e}")
                            
        # Handle referral completion for users who joined via referral and are already subscribed
        if not Config.is_sudo_user(user.id) and Config.MULTI_FSUB:
            subscription_status = await db.check_force_subscribe(user.id, client)
            if subscription_status['all_subscribed']:
                # User is already subscribed to all channels - check for any incomplete referrals
                user_data = await db.get_user(user.id)
                if user_data and user_data.get('referred_by') and not user_data.get('referral_completed'):
                    # Complete their referral immediately
                    logger.info(f"User {user.id} already subscribed to all channels, completing existing referral")
                    await db.mark_referral_bot_started(user.id)
                    referral_result = await db.mark_referral_channels_joined(user.id)
                    
                    # If referral was completed, send notifications
                    if referral_result and isinstance(referral_result, dict) and referral_result.get('completed'):
                        try:
                            from .fsub import _send_referral_completion_notifications
                            await _send_referral_completion_notifications(
                                client, 
                                referral_result['referrer_user_id'], 
                                referral_result['referred_user_id'],
                                referral_result['total_referrals'],
                                referral_result['reward_granted']
                            )
                            logger.info(f"Referral completion notifications sent for already subscribed user {user.id}")
                        except Exception as e:
                            logger.error(f"Error sending referral completion notifications for already subscribed user: {e}")
                
                # Also handle new referral setup if they came with a referral code
                elif referral_code and user_data and not user_data.get('referred_by'):
                    try:
                        # Check if referring user exists
                        referring_user = await db.get_user_by_referral_code(referral_code)
                        if referring_user:
                            # Set up and immediately complete referral
                            referral_success = await db.set_user_referred_by(user.id, referral_code)
                            if referral_success:
                                logger.info(f"✅ Set up referral for already subscribed user {user.id} via {referral_code}")
                                
                                # Immediately mark as completed since they're already subscribed
                                await db.mark_referral_bot_started(user.id)
                                referral_result = await db.mark_referral_channels_joined(user.id)
                                
                                # Send notifications
                                if referral_result and isinstance(referral_result, dict) and referral_result.get('completed'):
                                    try:
                                        from .fsub import _send_referral_completion_notifications
                                        await _send_referral_completion_notifications(
                                            client, 
                                            referral_result['referrer_user_id'], 
                                            referral_result['referred_user_id'],
                                            referral_result['total_referrals'],
                                            referral_result['reward_granted']
                                        )
                                        logger.info(f"Referral completion notifications sent for new referral on subscribed user {user.id}")
                                    except Exception as e:
                                        logger.error(f"Error sending referral completion notifications for new referral: {e}")
                        else:
                            logger.warning(f"No user found with referral code {referral_code} for subscribed user {user.id}")
                    except Exception as e:
                        logger.error(f"Error processing new referral for subscribed user {user.id}: {e}")

        reply_markup = InlineKeyboardMarkup(get_main_buttons())
        jishubotz = await message.reply_sticker("CAACAgUAAxkBAAEPclNo1mx0_aFOnH1b6tPdSxb_mRq90QACTBYAAiXVkVS0hQUwLAaSeTYE")
        await asyncio.sleep(2)
        await jishubotz.delete()
        text=Translation.START_TXT.format(user.mention)
        await message.reply_text(
            text=text,
            reply_markup=reply_markup,
            quote=True
        )
        logger.info(f"Start message sent to user {user.id}")
    except Exception as e:
        logger.error(f"Error in start command for user {user.id}: {e}", exc_info=True)
        await message.reply_text(
            "❌ An error occurred. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='back')]])
        )


# Premium plans callback handler
@Client.on_callback_query(filters.regex(r'^premium'))
async def premium_callback(client, callback_query):
    user_id = callback_query.from_user.id
    callback_data = callback_query.data

    if callback_data in ['premium_plans', 'premium#plans', 'premium#main']:
        # Get user's current plan
        current_plan = "FREE"
        plan_details = await db.get_premium_user_details(user_id)

        if plan_details:
            current_plan = plan_details.get('plan_type', 'FREE').upper()

        plans_text = (
            "💎 <b>Premium Plans</b>\n\n"
            f"👤 <b>Your Current Plan:</b> {current_plan}\n"
        )

        if plan_details and plan_details.get('expires_at'):
            from datetime import datetime
            expires_at = plan_details['expires_at']
            if expires_at > datetime.utcnow():
                plans_text += f"⏰ <b>Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M')}\n"

        plans_text += (
            "\n📋 <b>Available Plans:</b>\n\n"
            "🆓 <b>FREE PLAN</b>\n"
            "• 1 forwarding process per month\n"
            "• Basic features only\n"
            "• No FTM mode\n\n"

            "✨ <b>PLUS PLAN</b>\n"
            "• Unlimited forwarding processes\n"
            "• All basic features\n"
            "• No FTM mode\n"
            "• 15 days: ₹199\n"
            "• 30 days: ₹299\n\n"

            "🏆 <b>PRO PLAN</b>\n"
            "• Unlimited forwarding processes\n"
            "• FTM mode enabled\n"
            "• Priority support\n"
            "• All premium features\n"
            "• 15 days: ₹299\n"
            "• 30 days: ₹549\n\n"

            f"💳 <b>Payment:</b> UPI - {Config.UPI_ID}\n"
            "📸 <b>After payment, send screenshot with /verify</b>"
        )

        plans_buttons = [
            [
                InlineKeyboardButton("✨ Plus 15 Days (₹199)", callback_data="buy_plus_15"),
                InlineKeyboardButton("✨ Plus 30 Days (₹299)", callback_data="buy_plus_30")
            ],
            [
                InlineKeyboardButton("🏆 Pro 15 Days (₹299)", callback_data="buy_pro_15"),
                InlineKeyboardButton("🏆 Pro 30 Days (₹549)", callback_data="buy_pro_30")
            ],
            [
                InlineKeyboardButton("📊 My Plan Details", callback_data="my_plan"),
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]

        await callback_query.message.edit_text(
            text=plans_text,
            reply_markup=InlineKeyboardMarkup(plans_buttons)
        )



#==================Restart Function==================#

@Client.on_message(filters.private & filters.command(['restart', "r"]) & filters.user(Config.OWNER_ID))
async def restart(client, message):
    msg = await message.reply_text(
        text="<i>Trying To Restarting.....</i>",
        quote=True
    )
    await asyncio.sleep(5)
    await msg.edit("<i>Server Restarted Successfully ✅</i>")
    os.execl(sys.executable, sys.executable, *sys.argv)



#==================Callback Functions==================#

#==================Help Command==================#

@Client.on_message(filters.private & filters.command(['help']))
async def help_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Help command from user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        force_sub_text, force_buttons = await build_force_subscribe_message_and_buttons(client, user_id)
        if force_sub_text and force_buttons:
            return await message.reply_text(
                text=force_sub_text,
                reply_markup=force_buttons,
                quote=True
            )

        # Check if user is admin to show admin commands
        is_admin = Config.is_sudo_user(user_id)

        # Create help buttons
        buttons = [[
            InlineKeyboardButton('🛠️ How To Use Me 🛠️', callback_data='how_to_use')
        ],[
            InlineKeyboardButton('⚙️ Settings ⚙️', callback_data='settings#main'),
            InlineKeyboardButton('📊 Stats 📊', callback_data='status')
        ],[
            InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')
        ]]

        # Add admin commands button for admins only
        if is_admin:
            buttons.append([InlineKeyboardButton('👨‍💻 Admin Commands 👨‍💻', callback_data='admin_commands')])

        buttons.append([InlineKeyboardButton('🔙 Back', callback_data='back')])

        await message.reply_text(
            text=Translation.HELP_TXT.format(
                start="/start",
                trial="/trial",
                forward="/forward",
                settings="/settings",
                reset="/reset",
                speedtest="/speedtest",
                system="/system"
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        logger.debug(f"Help message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in help command for user {user_id}: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred. Please try again.")

@Client.on_callback_query(filters.regex(r'^help$'))
async def helpcb(bot, query):
    user_id = query.from_user.id
    logger.info(f"Help callback from user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        force_sub_text, force_buttons = await build_force_subscribe_message_and_buttons(bot, user_id)
        if force_sub_text and force_buttons:
            return await query.message.edit_text(
                text=force_sub_text,
                reply_markup=force_buttons
            )

        # Check if user is admin to show admin commands
        is_admin = Config.is_sudo_user(user_id)

        # Create help buttons
        buttons = [[
            InlineKeyboardButton('🛠️ How To Use Me 🛠️', callback_data='how_to_use')
        ],[
            InlineKeyboardButton('⚙️ Settings ⚙️', callback_data='settings#main'),
            InlineKeyboardButton('📊 Stats 📊', callback_data='status')
        ],[
            InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')
        ]]

        # Add admin commands button for admins only
        if is_admin:
            buttons.append([InlineKeyboardButton('👨‍💻 Admin Commands 👨‍💻', callback_data='admin_commands')])

        buttons.append([InlineKeyboardButton('🔙 Back', callback_data='back')])

        await query.message.edit_text(
            text=Translation.HELP_TXT.format(
                start="/start",
                trial="/trial",
                forward="/forward",
                settings="/settings",
                reset="/reset",
                speedtest="/speedtest",
                system="/system"
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        logger.debug(f"Help message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in help callback for user {user_id}: {e}", exc_info=True)


@Client.on_callback_query(filters.regex(r'^admin_commands$'))
async def admin_commands_callback(bot, query):
    user_id = query.from_user.id
    logger.info(f"Admin commands callback from user {user_id}")

    # Double-check admin status
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to access admin commands!", show_alert=True)

    try:
        admin_buttons = [[
            InlineKeyboardButton('💎 Add Premium', callback_data='admin_add_premium'),
            InlineKeyboardButton('❌ Remove Premium', callback_data='admin_remove_premium')
        ],[
            InlineKeyboardButton('👥 Premium Users', callback_data='admin_premium_users'),
            InlineKeyboardButton('💰 Change Price', callback_data='admin_change_price')
        ],[
            InlineKeyboardButton('💬 Start Chat', callback_data='admin_start_chat'),
            InlineKeyboardButton('📊 System Info', callback_data='admin_system')
        ],[
            InlineKeyboardButton('⚡ Speed Test', callback_data='admin_speedtest'),
            InlineKeyboardButton('🔄 Restart Bot', callback_data='admin_restart')
        ],[
            InlineKeyboardButton('🗑️ Reset All Users', callback_data='admin_resetall_info'),
            InlineKeyboardButton('🔙 Back to Help', callback_data='help')
        ]]

        await query.message.edit_text(
            text="<b>🔧 Admin Commands Panel</b>\n\n"
                 "<b>Premium Management Commands:</b>\n"
                 "• <code>/add_premium [user_id] [plan_type] [days]</code>\n"
                 "  Plan types: <b>plus</b> or <b>pro</b>\n"
                 "  Example: <code>/add_premium 123456789 pro 30</code>\n"
                 "• <code>/remove_premium [user_id]</code>\n\n"
                 "<b>User Management:</b>\n"
                 "• <code>/users</code> - List all registered users\n\n"
                 "<b>System Tools:</b> Monitor server performance\n"
                 "<b>User Support:</b> Direct chat with users\n"
                 "<b>Bot Control:</b> Restart and configuration\n\n"
                 "<i>These commands are only visible to admins and owners.</i>",
            reply_markup=InlineKeyboardMarkup(admin_buttons)
        )
        logger.debug(f"Admin commands panel sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in admin commands callback for user {user_id}: {e}", exc_info=True)


@Client.on_callback_query(filters.regex(r'^how_to_use'))
async def how_to_use(bot, query):
    user_id = query.from_user.id
    logger.info(f"How to use callback from user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        force_sub_text, force_buttons = await build_force_subscribe_message_and_buttons(bot, user_id)
        if force_sub_text and force_buttons:
            return await query.message.edit_text(
                text=force_sub_text,
                reply_markup=force_buttons
            )

        await query.message.edit_text(
            text=Translation.HOW_USE_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='help')]]),
            disable_web_page_preview=True
        )
        logger.debug(f"How to use message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in how_to_use callback for user {user_id}: {e}", exc_info=True)



@Client.on_callback_query(filters.regex(r'^back'))
async def back(bot, query):
    user_id = query.from_user.id
    logger.info(f"Back callback from user {user_id}")

    try:
        reply_markup = InlineKeyboardMarkup(get_main_buttons())
        await query.message.edit_text(
           reply_markup=reply_markup,
           text=Translation.START_TXT.format(
                    query.from_user.first_name))
        logger.debug(f"Back to main menu for user {user_id}")
    except Exception as e:
        logger.error(f"Error in back callback for user {user_id}: {e}", exc_info=True)



@Client.on_callback_query(filters.regex(r'^about'))
async def about(bot, query):
    user_id = query.from_user.id
    logger.info(f"About callback from user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        force_sub_text, force_buttons = await build_force_subscribe_message_and_buttons(bot, user_id)
        if force_sub_text and force_buttons:
            return await query.message.edit_text(
                text=force_sub_text,
                reply_markup=force_buttons
            )

        await query.message.edit_text(
            text=Translation.ABOUT_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='back')]]),
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
        )
        logger.debug(f"About message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in about callback for user {user_id}: {e}", exc_info=True)



@Client.on_callback_query(filters.regex(r'^get_free_trial$'))
async def trial_callback(client, callback_query):
    """Handle get free trial button"""
    user_id = callback_query.from_user.id
    logger.info(f"Trial callback from user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id) and Config.MULTI_FSUB:
            subscription_status = await db.check_force_subscribe(user_id, client)
            if not subscription_status['all_subscribed']:
                force_buttons, joined_channels = await get_force_sub_buttons(client, user_id)
                if force_buttons:
                    force_sub_text = Translation.FORCE_SUBSCRIBE_MSG
                    if joined_channels:
                        force_sub_text += f"\n\n<b>✅ Already Joined:</b>\n"
                        for channel in joined_channels:
                            force_sub_text += f"• {channel} ✅\n"
                        force_sub_text += f"\n<b>📢 Please join the remaining channels below:</b>"

                    return await callback_query.message.edit_text(
                        text=force_sub_text,
                        reply_markup=InlineKeyboardMarkup(force_buttons)
                    )


        # Check if user can use trial
        can_trial = await db.can_use_trial(user_id)

        if not can_trial:
            await callback_query.answer("❌ Trial already used this year!", show_alert=True)
            return

        # Check if user already has premium
        is_premium = await db.is_premium_user(user_id)
        if is_premium:
            await callback_query.answer("✅ You already have premium access!", show_alert=True)
            return

        # Show confirmation
        await callback_query.message.edit_text(
            text="<b>🎁 Activate Free Trial?</b>\n\n"
                 "<b>✅ 3 days unlimited forwarding</b>\n"
                 "<b>✅ All premium features (except FTM mode)</b>\n"
                 "<b>✅ Priority support</b>\n\n"
                 "<b>⚠️ Available once per year only!</b>\n\n"
                 "<b>Do you want to activate your free trial now?</b>",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton('✅ Yes, Activate Trial', callback_data='confirm_trial'),
                    InlineKeyboardButton('❌ Not Now', callback_data='back')
                ]
            ])
        )

    except Exception as e:
        logger.error(f"Error in trial callback for user {user_id}: {e}", exc_info=True)
        await callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex(r'^confirm_trial$'))
async def confirm_trial_callback(client, callback_query):
    """Handle trial confirmation"""
    user_id = callback_query.from_user.id

    try:
        # Grant trial
        success, result = await db.grant_trial(user_id)

        if success:
            from plugins.timezone import display_expiry_date
            expires_date = display_expiry_date(result)
            await callback_query.message.edit_text(
                text=f"<b>🎉 3-Day Trial Activated!</b>\n\n"
                     f"<b>✅ You now have unlimited forwarding for 3 days!</b>\n\n"
                     f"<b>Trial Benefits:</b>\n"
                     f"• ✅ Unlimited forwarding processes\n"
                     f"• ✅ All premium features (except FTM mode)\n"
                     f"• ✅ Priority support\n\n"
                     f"<b>⏰ Expires:</b> {expires_date}\n\n"
                     f"<b>💡 Use /forward to start forwarding messages!</b>",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton('📊 My Plan', callback_data='my_plan'),
                        InlineKeyboardButton('🚀 Start Forwarding', callback_data='start_forwarding')
                    ],
                    [
                        InlineKeyboardButton('🏠 Main Menu', callback_data='back')
                    ]
                ])
            )

            # Send notification
            notify = NotificationManager(client)
            await notify.notify_user_action(
                user_id,
                "Trial Activated",
                f"User activated 3-day free trial - expires {expires_date}"
            )

        else:
            await callback_query.message.edit_text(
                text=f"<b>❌ Trial Activation Failed</b>\n\n"
                     f"<b>Reason:</b> {result}\n\n"
                     f"<b>💎 Check our premium plans with /plan</b>",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🏠 Main Menu', callback_data='back')
                ]])
            )

    except Exception as e:
        logger.error(f"Error in confirm trial for user {user_id}: {e}", exc_info=True)
        await callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex(r'^start_forwarding$'))
async def start_forwarding_callback(client, callback_query):
    """Handle start forwarding button"""
    await callback_query.message.edit_text(
        text="<b>🚀 Ready to Forward!</b>\n\n"
             "<b>Use the /forward command to start forwarding messages.</b>\n\n"
             "<b>Before forwarding, make sure you have:</b>\n"
             "• ✅ Added your bot in /settings\n"
             "• ✅ Added target channels in /settings\n"
             "• ✅ Made your bot admin in target channels\n\n"
             "<b>💡 Need help? Use /help for detailed instructions.</b>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton('⚙️ Settings', callback_data='settings#main'),
                InlineKeyboardButton('📋 Help', callback_data='help')
            ],
            [
                InlineKeyboardButton('🏠 Main Menu', callback_data='back')
            ]
        ])
    )

@Client.on_callback_query(filters.regex(r'^status'))
async def status(bot, query):
    user_id = query.from_user.id
    logger.info(f"Status callback from user {user_id}")

    try:
        # Check force subscribe for non-sudo users
        force_sub_text, force_buttons = await build_force_subscribe_message_and_buttons(bot, user_id)
        if force_sub_text and force_buttons:
            return await query.message.edit_text(
                text=force_sub_text,
                reply_markup=force_buttons
            )

        users_count, bots_count = await db.total_users_bots_count()
        total_channels = await db.total_channels()
        await query.message.edit_text(
            text=Translation.STATUS_TXT.format(users_count, bots_count, temp.forwardings, total_channels),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='help')]]),
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
        logger.debug(f"Status message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in status callback for user {user_id}: {e}", exc_info=True)


#==================Speedtest Command==================#

@Client.on_message(filters.private & filters.command(['speedtest', 'speed']))
async def speed_test_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Speedtest command from user {user_id}")

    # Check if user is sudo (owner or admin)
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ This command is only available for administrators.")

    status_msg = await message.reply_text("🔄 <b>Running Network Speed Test...</b>\n⏳ Please wait, this may take a moment.")

    try:
        # Initialize speedtest
        st = speedtest.Speedtest()

        # Update status
        await status_msg.edit_text("🔄 <b>Finding best server...</b>\n⏳ Please wait.")

        # Get best server
        st.get_best_server()

        # Update status
        await status_msg.edit_text("🔄 <b>Testing download speed...</b>\n⏳ Please wait.")

        # Test download speed
        download_speed = st.download()

        # Update status
        await status_msg.edit_text("🔄 <b>Testing upload speed...</b>\n⏳ Please wait.")

        # Test upload speed
        upload_speed = st.upload()

        # Get ping
        ping = st.results.ping

        # Get server info
        server = st.get_best_server()

        # Convert bytes to Mbps
        download_mbps = download_speed / 1024 / 1024
        upload_mbps = upload_speed / 1024 / 1024

        # Format the result
        speed_text = f"""<b>🌐 Bot Server Network Speed Test</b>

<b>📡 Server Connection Info:</b>
├ <b>ISP:</b> <code>{server.get('sponsor', 'Unknown')}</code>
├ <b>Server Location:</b> <code>{server.get('name', 'Unknown')}, {server.get('country', 'Unknown')}</code>
├ <b>Distance:</b> <code>{server.get('d', 0):.1f} km</code>

<b>🚀 Bot Server Speed Results:</b>
├ <b>📥 Download:</b> <code>{download_mbps:.2f} Mbps</code>
├ <b>📤 Upload:</b> <code>{upload_mbps:.2f} Mbps</code>
├ <b>📶 Ping:</b> <code>{ping:.1f} ms</code>

<b>📊 Test Information:</b>
├ <b>Test Date:</b> <code>{st.results.timestamp}</code>
├ <b>Note:</b> <code>Shows bot server network, not your location</code>
└ <b>Share URL:</b> <a href="{st.results.share()}">View Results</a>"""

        await status_msg.edit_text(speed_text, disable_web_page_preview=True)
        logger.info(f"Speedtest completed for user {user_id}")

    except Exception as e:
        error_msg = f"❌ <b>Speed Test Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(error_msg)
        logger.error(f"Speedtest error for user {user_id}: {e}", exc_info=True)


#==================System Info Command==================#

@Client.on_message(filters.private & filters.command(['system', 'sys', 'sysinfo']))
async def system_info_command(client, message):
    user_id = message.from_user.id
    logger.info(f"System info command from user {user_id}")

    # Check if user is sudo (owner or admin)
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ This command is only available for administrators.")

    status_msg = await message.reply_text("🔄 <b>Gathering system information...</b>")

    try:
        # Get system info
        uname = platform.uname()

        # Get CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()

        # Get memory info
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024**3)  # GB
        memory_used = memory.used / (1024**3)   # GB
        memory_percent = memory.percent

        # Get disk info
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3)  # GB
        disk_used = disk.used / (1024**3)    # GB
        disk_percent = (disk.used / disk.total) * 100

        # Get network info
        net_io = psutil.net_io_counters()
        bytes_sent = net_io.bytes_sent / (1024**2)  # MB
        bytes_recv = net_io.bytes_recv / (1024**2)  # MB

        # Get boot time
        boot_time = psutil.boot_time()

        # Get process info
        process_count = len(psutil.pids())

        # Get Python info
        python_ver = python_version()

        # Format uptime
        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
        uptime_str = str(uptime).split('.')[0]

        # Get load average (Unix-like systems)
        try:
            load_avg = os.getloadavg()
            load_str = f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
        except:
            load_str = "Not Available"

        system_text = f"""<b>🖥️ Bot Server System Information</b>

<b>💻 Server System Details:</b>
├ <b>OS:</b> <code>{uname.system} {uname.release}</code>
├ <b>Architecture:</b> <code>{uname.machine}</code>
├ <b>Hostname:</b> <code>{uname.node}</code>
├ <b>Kernel:</b> <code>{uname.version}</code>

<b>🔧 Server Hardware Info:</b>
├ <b>CPU Cores:</b> <code>{cpu_count} cores</code>
├ <b>CPU Usage:</b> <code>{cpu_percent}%</code>
├ <b>CPU Frequency:</b> <code>{cpu_freq.current:.0f} MHz</code> (Max: <code>{cpu_freq.max:.0f} MHz</code>)
├ <b>Load Average:</b> <code>{load_str}</code>

<b>💾 Server Memory Info:</b>
├ <b>Total RAM:</b> <code>{memory_total:.2f} GB</code>
├ <b>Used RAM:</b> <code>{memory_used:.2f} GB ({memory_percent}%)</code>
├ <b>Available RAM:</b> <code>{(memory_total - memory_used):.2f} GB</code>

<b>💿 Server Storage Info:</b>
├ <b>Total Disk:</b> <code>{disk_total:.2f} GB</code>
├ <b>Used Disk:</b> <code>{disk_used:.2f} GB ({disk_percent:.1f}%)</code>
├ <b>Free Disk:</b> <code>{(disk_total - disk_used):.2f} GB</code>

<b>🌐 Server Network Usage:</b>
├ <b>Data Sent:</b> <code>{bytes_sent:.2f} MB</code>
├ <b>Data Received:</b> <code>{bytes_recv:.2f} MB</code>

<b>⚡ Bot Runtime Info:</b>
├ <b>Python Version:</b> <code>v{python_ver}</code>
├ <b>Pyrogram Version:</b> <code>v{pyrogram_version}</code>
├ <b>Active Processes:</b> <code>{process_count}</code>
├ <b>Server Uptime:</b> <code>{uptime_str}</code>
├ <b>Note:</b> <code>Shows bot server stats, not your device</code>
└ <b>Bot Status:</b> <code>Running ✅</code>"""

        await status_msg.edit_text(system_text)
        logger.info(f"System info sent to user {user_id}")

    except Exception as e:
        error_msg = f"❌ <b>System Info Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(error_msg)
        logger.error(f"System info error for user {user_id}: {e}", exc_info=True)


#==================Admin Callback Functions==================#

@Client.on_callback_query(filters.regex(r'^admin_change_price$'))
async def admin_change_price_callback(bot, query):
    user_id = query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)

    try:
        await query.message.edit_text(
            text=f"<b>💰 Current Premium Price</b>\n\n"
                 f"<b>Current Price:</b> ₹{Config.PREMIUM_PRICE}/month\n\n"
                 f"<b>To change the price:</b>\n"
                 f"1. Update the PREMIUM_PRICE environment variable\n"
                 f"2. Restart the bot to apply changes\n\n"
                 f"<i>Note: Price changes require bot restart</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_system$'))
async def admin_system_callback(bot, query):
    user_id = query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)

    # Call system info logic directly instead of redirecting to command handler
    status_msg = await query.message.edit_text("🔄 <b>Gathering system information...</b>")

    try:
        # Get system info
        uname = platform.uname()

        # Get CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()

        # Get memory info
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024**3)  # GB
        memory_used = memory.used / (1024**3)   # GB
        memory_percent = memory.percent

        # Get disk info
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3)  # GB
        disk_used = disk.used / (1024**3)    # GB
        disk_percent = (disk.used / disk.total) * 100

        # Get network info
        net_io = psutil.net_io_counters()
        bytes_sent = net_io.bytes_sent / (1024**2)  # MB
        bytes_recv = net_io.bytes_recv / (1024**2)  # MB

        # Get boot time
        boot_time = psutil.boot_time()

        # Get process info
        process_count = len(psutil.pids())

        # Get Python info
        python_ver = python_version()

        # Format uptime
        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
        uptime_str = str(uptime).split('.')[0]

        # Get load average (Unix-like systems)
        try:
            load_avg = os.getloadavg()
            load_str = f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
        except:
            load_str = "Not Available"

        system_text = f"""<b>🖥️ Bot Server System Information</b>

<b>💻 Server System Details:</b>
├ <b>OS:</b> <code>{uname.system} {uname.release}</code>
├ <b>Architecture:</b> <code>{uname.machine}</code>
├ <b>Hostname:</b> <code>{uname.node}</code>
├ <b>Kernel:</b> <code>{uname.version}</code>

<b>🔧 Server Hardware Info:</b>
├ <b>CPU Cores:</b> <code>{cpu_count} cores</code>
├ <b>CPU Usage:</b> <code>{cpu_percent}%</code>
├ <b>CPU Frequency:</b> <code>{cpu_freq.current:.0f} MHz</code> (Max: <code>{cpu_freq.max:.0f} MHz</code>)
├ <b>Load Average:</b> <code>{load_str}</code>

<b>💾 Server Memory Info:</b>
├ <b>Total RAM:</b> <code>{memory_total:.2f} GB</code>
├ <b>Used RAM:</b> <code>{memory_used:.2f} GB ({memory_percent}%)</code>
├ <b>Available RAM:</b> <code>{(memory_total - memory_used):.2f} GB</code>

<b>💿 Server Storage Info:</b>
├ <b>Total Disk:</b> <code>{disk_total:.2f} GB</code>
├ <b>Used Disk:</b> <code>{disk_used:.2f} GB ({disk_percent:.1f}%)</code>
├ <b>Free Disk:</b> <code>{(disk_total - disk_used):.2f} GB</code>

<b>🌐 Server Network Usage:</b>
├ <b>Data Sent:</b> <code>{bytes_sent:.2f} MB</code>
├ <b>Data Received:</b> <code>{bytes_recv:.2f} MB</code>

<b>⚡ Bot Runtime Info:</b>
├ <b>Python Version:</b> <code>v{python_ver}</code>
├ <b>Pyrogram Version:</b> <code>v{pyrogram_version}</code>
├ <b>Active Processes:</b> <code>{process_count}</code>
├ <b>Server Uptime:</b> <code>{uptime_str}</code>
├ <b>Note:</b> <code>Shows bot server stats, not your device</code>
└ <b>Bot Status:</b> <code>Running ✅</code>"""

        await status_msg.edit_text(
            text=system_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
        logger.info(f"System info sent to admin {user_id}")

    except Exception as e:
        error_msg = f"❌ <b>System Info Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(
            text=error_msg,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
        logger.error(f"System info error for admin {user_id}: {e}", exc_info=True)

@Client.on_callback_query(filters.regex(r'^admin_speedtest$'))
async def admin_speedtest_callback(bot, query):
    user_id = query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)

    # Call speedtest logic directly instead of redirecting to command handler
    status_msg = await query.message.edit_text("🔄 <b>Running Network Speed Test...</b>\n⏳ Please wait, this may take a moment.")

    try:
        # Initialize speedtest
        st = speedtest.Speedtest()

        # Update status
        await status_msg.edit_text("🔄 <b>Finding best server...</b>\n⏳ Please wait.")

        # Get best server
        st.get_best_server()

        # Update status
        await status_msg.edit_text("🔄 <b>Testing download speed...</b>\n⏳ Please wait.")

        # Test download speed
        download_speed = st.download()

        # Update status
        await status_msg.edit_text("🔄 <b>Testing upload speed...</b>\n⏳ Please wait.")

        # Test upload speed
        upload_speed = st.upload()

        # Get ping
        ping = st.results.ping

        # Get server info
        server = st.get_best_server()

        # Convert bytes to Mbps
        download_mbps = download_speed / 1024 / 1024
        upload_mbps = upload_speed / 1024 / 1024

        # Format the result
        speed_text = f"""<b>🌐 Bot Server Network Speed Test</b>

<b>📡 Server Connection Info:</b>
├ <b>ISP:</b> <code>{server.get('sponsor', 'Unknown')}</code>
├ <b>Server Location:</b> <code>{server.get('name', 'Unknown')}, {server.get('country', 'Unknown')}</code>
├ <b>Distance:</b> <code>{server.get('d', 0):.1f} km</code>

<b>🚀 Bot Server Speed Results:</b>
├ <b>📥 Download:</b> <code>{download_mbps:.2f} Mbps</code>
├ <b>📤 Upload:</b> <code>{upload_mbps:.2f} Mbps</code>
├ <b>📶 Ping:</b> <code>{ping:.1f} ms</code>

<b>📊 Test Information:</b>
├ <b>Test Date:</b> <code>{st.results.timestamp}</code>
├ <b>Note:</b> <code>Shows bot server network, not your location</code>
└ <b>Share URL:</b> <a href="{st.results.share()}">View Results</a>"""

        await status_msg.edit_text(
            text=speed_text, 
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
        logger.info(f"Speedtest completed for admin {user_id}")

    except Exception as e:
        error_msg = f"❌ <b>Speed Test Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(
            text=error_msg,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
        logger.error(f"Speedtest error for admin {user_id}: {e}", exc_info=True)

@Client.on_callback_query(filters.regex(r'^admin_restart$'))
async def admin_restart_callback(bot, query):
    user_id = query.from_user.id

    if user_id not in Config.OWNER_ID:
        return await query.answer("❌ Only owners can restart the bot!", show_alert=True)

    try:
        await query.message.edit_text(
            text="<b>🔄 Bot Restart</b>\n\n"
                 "<b>⚠️ Are you sure you want to restart the bot?</b>\n\n"
                 "<i>This will stop all ongoing processes!</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('✅ Yes, Restart', callback_data='confirm_restart'),
                InlineKeyboardButton('❌ Cancel', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^confirm_restart$'))
async def confirm_restart_callback(bot, query):
    user_id = query.from_user.id

    if user_id not in Config.OWNER_ID:
        return await query.answer("❌ Only owners can restart the bot!", show_alert=True)

    await query.message.edit_text("🔄 <b>Restarting bot...</b>\n\n<i>Please wait...</i>")
    await restart(bot, query.message)

@Client.on_callback_query(filters.regex(r'^admin_add_premium$'))
async def admin_add_premium_callback(bot, query):
    user_id = query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)

    try:
        await query.message.edit_text(
            text="<b>💎 Add Premium User</b>\n\n"
                 "<b>How to add premium:</b>\n\n"
                 "1. Use command: <code>/add_premium [user_id] [days]</code>\n"
                 "2. Example: <code>/add_premium 123456789 30</code>\n\n"
                 "<b>Default:</b> 30 days if days not specified\n\n"
                 "<i>Use this command in chat, not through buttons</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_remove_premium$'))
async def admin_remove_premium_callback(bot, query):
    user_id = query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)

    try:
        await query.message.edit_text(
            text="<b>❌ Remove Premium User</b>\n\n"
                 "<b>How to remove premium:</b>\n\n"
                 "1. Use command: <code>/remove_premium [user_id]</code>\n"
                 "2. Example: <code>/remove_premium 123456789</code>\n\n"
                 "<i>Use this command in chat, not through buttons</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_premium_users$'))
async def admin_premium_users_callback(bot, query):
    user_id = query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)

    try:
        await query.message.edit_text(
            text="<b>👥 Premium Users List</b>\n\n"
                 "<b>How to view premium users:</b>\n\n"
                 "1. Use command: <code>/pusers</code>\n\n"
                 "<i>Use this command in chat for detailed list</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_start_chat$'))
async def admin_start_chat_callback(bot, query):
    user_id = query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)

    try:
        await query.message.edit_text(
            text="<b>💬 Start Admin Chat</b>\n\n"
                 "<b>How to start chat with user:</b>\n\n"
                 "1. Use command: <code>/chat [user_id]</code>\n"
                 "2. Example: <code>/chat 123456789</code>\n\n"
                 "<b>To end chat:</b> <code>/endchat</code>\n\n"
                 "<i>Use these commands in chat, not through buttons</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_resetall_info$'))
async def admin_resetall_info_callback(bot, query):
    user_id = query.from_user.id

    if user_id not in Config.OWNER_ID:
        return await query.answer("❌ Only owners can reset all users!", show_alert=True)

    try:
        await query.message.edit_text(
            text="<b>🗑️ Reset Commands Information</b>\n\n"
                 "<b>Available Reset Commands:</b>\n\n"
                 "<b>1. Individual User Reset:</b>\n"
                 "• Command: <code>/reset</code>\n"
                 "• Resets your own data only\n"
                 "• Available to all users\n\n"
                 "<b>2. Reset All Users (Owner Only):</b>\n"
                 "• Command: <code>/resetall</code>\n"
                 "• Resets ALL users' data\n"
                 "• Only available to owners\n\n"
                 "<b>⚠️ Warning:</b> Reset commands will permanently delete:\n"
                 "• All configurations\n"
                 "• All bot connections\n"
                 "• All channel settings\n"
                 "• All custom preferences\n\n"
                 "<b>❗ These actions cannot be undone!</b>\n\n"
                 "<i>Use these commands in chat for full functionality</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

#==================Free Trial & Contact Handlers==================#

@Client.on_callback_query(filters.regex(r'^get_free_trial$'))
async def get_free_trial_callback(bot, query):
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    logger.info(f"Free trial requested by user {user_id} ({user_name})")

    try:
        # Check if user can use free trial
        can_trial = await db.can_use_trial(user_id)

        if not can_trial:
            await query.answer(
                "❌ You have already used your free trial this year!\n"
                "💎 Upgrade to Premium for unlimited access.",
                show_alert=True
            )
            return

        if await db.is_premium_user(user_id):
            await query.answer(
                "✅ You already have Premium access!\n"
                "No need for free trial - you have unlimited processes.",
                show_alert=True
            )
            return

        # Grant the free trial (add 1 extra process - total 2 for this month)
        trial_granted = await db.add_trial_processes(user_id, 1)

        if not trial_granted:
            await query.answer(
                "❌ You have already claimed your free trial this month!\n"
                "💎 Upgrade to Premium for unlimited access.",
                show_alert=True
            )
            return

        # Send notification to admins
        try:
            notify = NotificationManager(bot)
            await notify.notify_free_trial_activity(
                user_id=user_id,
                action="activated free trial",
                remaining_usage=1  # User now has 2 total processes (1 base + 1 trial)
            )
        except Exception as notify_err:
            logger.error(f"Failed to send free trial notification: {notify_err}")

        # Send confirmation message to user
        await query.message.edit_text(
            text="<b>🎉 Free Trial Activated!</b>\n\n"
                 "<b>✅ You have received +1 additional process for this month!</b>\n\n"
                 "<b>📋 Your monthly allowance:</b>\n"
                 "• Base free plan: 1 process\n"
                 "• Trial bonus: +1 process\n"
                 "• <b>Total available: 2 processes</b>\n\n"
                 "<b>What you can do:</b>\n"
                 "• Use /forward to start forwarding messages\n"
                 "• Process two forwarding jobs this month\n\n"
                 "<b>💎 Want unlimited access?</b>\n"
                 "Upgrade to Premium:\n"
                 "• <b>Plus Plan:</b> ₹199/15d, ₹299/30d - Unlimited forwarding\n"
                 "• <b>Pro Plan:</b> ₹299/15d, ₹549/30d - Unlimited + FTM Mode + Priority support\n\n"
                 "<b>🗓️ Resets:</b> 1st of next month",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🚀 Start Forwarding', callback_data='settings#main')],
                [InlineKeyboardButton('💎 Upgrade to Premium', callback_data='premium_info')],
                [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
            ])
        )

        logger.info(f"Free trial granted to user {user_id}")

    except Exception as e:
        logger.error(f"Error in free trial callback for user {user_id}: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex(r'^contact_admin$'))
async def contact_admin_callback(bot, query):
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    user_username = f"@{query.from_user.username}" if query.from_user.username else ""
    logger.info(f"Contact admin callback from user {user_id} ({user_name})")

    try:
        # Check if user already has a pending chat request
        existing_request = await db.get_pending_chat_request(user_id)
        if existing_request:
            await query.answer(
                "⏳ You already have a pending chat request.\n"
                "Please wait for admin approval.",
                show_alert=True
            )
            return

        # Check if user is already in an active chat
        active_chat = await db.get_active_chat_for_user(user_id)
        if active_chat:
            await query.answer(
                "💬 You already have an active chat session with admin!\n"
                "Just send your message and it will be forwarded.",
                show_alert=True
            )
            return

        # Create chat request
        request_id = await db.create_chat_request(user_id)

        # Notification for contact request
        try:
            from utils.notifications import NotificationManager
            notification_manager = NotificationManager(bot)
            await notification_manager.notify_contact_request(
                user_id=user_id,
                request_type="general support",
                status="submitted"
            )
        except Exception as notif_err:
            logger.error(f"Failed to send contact request notification: {notif_err}")

        await query.message.edit_text(
            text="<b>💬 Contact Request Submitted!</b>\n\n"
                 "<b>Your request to contact admin has been submitted.</b>\n"
                 "<b>⏳ Please wait for admin approval.</b>\n\n"
                 f"<b>Request ID:</b> <code>{request_id}</code>\n"
                 "<b>💬 You will be notified once an admin accepts your request.</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
            ])
        )

        # Send notification to all sudo users (admin + owner) with accept/deny options
        sudo_users = Config.OWNER_ID + Config.ADMIN_ID

        for sudo_id in sudo_users:
            try:
                buttons = [
                    [
                        InlineKeyboardButton("✅ Accept Chat", callback_data=f"accept_chat_{request_id}"),
                        InlineKeyboardButton("❌ Deny", callback_data=f"deny_chat_{request_id}")
                    ]
                ]

                await bot.send_message(
                    sudo_id,
                    f"<b>💬 New Contact Request</b>\n\n"
                    f"<b>User:</b> {user_name} {user_username}\n"
                    f"<b>User ID:</b> <code>{user_id}</code>\n"
                    f"<b>Request ID:</b> <code>{request_id}</code>\n"
                    f"<b>Time:</b> {get_current_ist_timestamp()}\n\n"
                    f"<b>Choose an action:</b>",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as send_err:
                logger.error(f"Failed to send contact request to admin {sudo_id}: {send_err}")

        logger.info(f"Contact request created: {request_id} for user {user_id}")

    except Exception as e:
        logger.error(f"Error in contact admin callback for user {user_id}: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex(r'^premium_info$'))
async def premium_info_callback(bot, query):
    user_id = query.from_user.id
    logger.info(f"Premium info callback from user {user_id}")

    try:
        # Notification for plan exploration
        try:
            from utils.notifications import NotificationManager
            notification_manager = NotificationManager(bot)
            await notification_manager.notify_plan_exploration(
                user_id=user_id,
                plan_type="Premium Plan Information",
                action="viewed premium info",
                source="main menu button"
            )
        except Exception as notif_err:
            logger.error(f"Failed to send plan exploration notification: {notif_err}")

        await query.message.edit_text(
            text=Translation.PLAN_INFO_MSG,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('📊 Check My Plan', callback_data='my_plan')],
                [InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')],
                [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
            ])
        )
    except Exception as e:
        logger.error(f"Error in premium info callback for user {user_id}: {e}", exc_info=True)

@Client.on_callback_query(filters.regex(r'^my_plan$'))
async def my_plan_callback(bot, query):
    user_id = query.from_user.id
    logger.info(f"My plan callback from user {user_id}")

    try:
        # Notification for plan exploration
        try:
            from utils.notifications import NotificationManager
            notification_manager = NotificationManager(bot)
            await notification_manager.notify_plan_exploration(
                user_id=user_id,
                plan_type="Current Plan Status",
                action="checked current plan",
                source="premium info menu"
            )
        except Exception as notif_err:
            logger.error(f"Failed to send plan exploration notification: {notif_err}")

        # Check user's plan status
        premium_info = await db.get_premium_user_details(user_id)
        daily_usage = await db.get_daily_usage(user_id)
        usage_count = daily_usage.get('processes', 0)

        if premium_info:
            # User has active premium plan
            plan_type = premium_info.get('plan_type', 'unknown')
            expires_at = premium_info.get('expires_at', 'Unknown')
            # Calculate days remaining
            from datetime import datetime
            expires_at_obj = premium_info.get('expires_at', datetime.utcnow())
            if isinstance(expires_at_obj, datetime):
                days_remaining = max(0, (expires_at_obj - datetime.utcnow()).days)
            else:
                days_remaining = 0

            if plan_type.lower() == 'plus':
                plan_text = f"""<b>✨ Your Plus Plan</b>

<b>✅ Status:</b> Plus Plan Active
<b>📅 Plan Type:</b> Plus (15-30 days)
<b>⏰ Expires:</b> {expires_at}
<b>⏱️ Days Left:</b> {days_remaining} days
<b>📊 This Month:</b> {usage_count} processes used

<b>🎯 Plus Plan Features:</b>
• ♾️ Unlimited forwarding processes
• ⚡ Standard processing speed
• 🔄 Basic filtering options
• 📱 Standard support

<b>💡 Upgrade to Pro for:</b>
• 🔥 FTM Mode with source tracking
• 🛡️ Priority support
• 🚀 Enhanced performance"""
            elif plan_type.lower() == 'pro':
                plan_text = f"""<b>🔥 Your Pro Plan</b>

<b>✅ Status:</b> Pro Plan Active
<b>📅 Plan Type:</b> Pro (15-30 days)
<b>⏰ Expires:</b> {expires_at}
<b>⏱️ Days Left:</b> {days_remaining} days
<b>📊 This Month:</b> {usage_count} processes used

<b>🚀 Pro Plan Features:</b>
• ♾️ Unlimited forwarding processes
• 🔥 FTM Mode with source tracking
• ⚡ Priority processing speed
• 🛠️ Advanced filtering options
• 🛡️ Priority customer support
• 📈 Enhanced performance"""
            else:
                plan_text = f"""<b>💎 Your Premium Plan</b>

<b>✅ Status:</b> Premium Active
<b>📅 Plan Type:</b> {plan_type}
<b>⏰ Expires:</b> {expires_at}
<b>🔄 Usage:</b> Unlimited processes
<b>📊 This Month:</b> {usage_count} processes used

<b>🎉 You have access to premium features!</b>"""
        else:
            # User is on free plan - get monthly usage
            monthly_usage = await db.get_monthly_usage(user_id)
            processes_used = monthly_usage.get('processes', 0)

            # Check trial status for proper limit calculation
            trial_status = await db.get_trial_status(user_id)
            processes_limit = 1  # Base free process
            trial_text = ""
            if trial_status and trial_status.get('used', False):
                processes_limit = 2  # Base + trial
                trial_text = " (1 base + 1 trial)"

            plan_text = f"""<b>🆓 Your Free Plan</b>

<b>📊 Status:</b> Free User
<b>🔄 Monthly Usage:</b> {processes_used}/{processes_limit} processes
<b>🗓️ Usage Resets:</b> 1st of each month
<b>📈 Remaining:</b> {max(0, processes_limit - processes_used)} free processes

<b>💡 Current Features:</b>
• {processes_limit}️⃣ {processes_limit} free process{'es' if processes_limit > 1 else ''} per month{trial_text}
• 🔄 Basic forwarding functionality
• 📋 Standard filtering options

<b>🚀 Available Plans:</b>
<b>✨ Plus Plan:</b> ₹{Config.PLAN_PRICING['plus']['15_days']}/15d, ₹{Config.PLAN_PRICING['plus']['30_days']}/30d
• Unlimited forwarding

<b>🔥 Pro Plan:</b> ₹{Config.PLAN_PRICING['pro']['15_days']}/15d, ₹{Config.PLAN_PRICING['pro']['30_days']}/30d
• Unlimited forwarding + FTM Mode + Priority support"""

        buttons = []
        if not premium_info:
            # Free user - show upgrade options
            buttons.append([InlineKeyboardButton('💎 Upgrade Now', callback_data='premium#main')])
        elif premium_info.get('plan_type', '').lower() == 'plus':
            # Plus user - show Pro upgrade option
            buttons.append([InlineKeyboardButton('🔥 Upgrade to Pro', callback_data='premium#main')])

        buttons.extend([
            [
                InlineKeyboardButton('🔗 Referral System', callback_data='refresh_referral'),
                InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')
            ],
            [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
        ])

        await query.message.edit_text(
            text=plan_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error in my plan callback for user {user_id}: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

# /info command for users to get all their information
# /info command removed - now handled by python-telegram-bot in ptb_commands.py

# Helper function to generate users list text and buttons
async def generate_users_list(page=1):
    """Generate users list with pagination"""
    # Get all users from database
    all_users = await db.get_all_users()

    if not all_users:
        return "📋 No registered users found.", []

    # Pagination settings
    users_per_page = 10
    total_pages = (len(all_users) + users_per_page - 1) // users_per_page

    # Ensure page is within bounds
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * users_per_page
    end_idx = min(start_idx + users_per_page, len(all_users))

    # Count statistics
    premium_count = plus_count = pro_count = free_count = active_today = 0

    from datetime import datetime, timedelta
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Enhanced header with statistics
    users_text = f"<b>👥 All Registered Users</b>\n\n"
    users_text += f"<b>📄 Page {page} of {total_pages}</b>\n"
    users_text += f"<b>📊 Total Users: {len(all_users)}</b>\n"
    users_text += f"{'='*40}\n\n"

    # Process users for current page
    for i, user_info in enumerate(all_users[start_idx:end_idx], start_idx + 1):
        user_id_info = user_info.get('id', 'Unknown')
        user_name = user_info.get('name', 'Unknown')
        joined_date = user_info.get('joined_date', 'Unknown')

        # Check if user has premium
        premium_info = await db.get_premium_user_details(user_id_info)
        if premium_info:
            plan_type = premium_info.get('plan_type', 'premium').upper()
            if plan_type == 'PRO':
                status = "💎 PRO"
                pro_count += 1
            elif plan_type == 'PLUS':
                status = "💎 PLUS"
                plus_count += 1
            else:
                status = f"💎 {plan_type}"
                premium_count += 1

            # Check expiry
            expires_at = premium_info.get('expires_at')
            if expires_at and isinstance(expires_at, datetime):
                days_left = (expires_at - datetime.utcnow()).days
                if days_left <= 0:
                    status += " (EXPIRED)"
                elif days_left <= 3:
                    status += f" ({days_left}d)"
        else:
            status = "🆓 FREE"
            free_count += 1

        # Format join date and check if active today
        if isinstance(joined_date, datetime):
            join_str = joined_date.strftime('%Y-%m-%d')
            if joined_date >= today:
                active_today += 1
        else:
            join_str = "Unknown"

        # Truncate long names for better display
        display_name = user_name[:20] + "..." if len(user_name) > 20 else user_name

        users_text += f"<b>{i}.</b> <b>{display_name}</b>\n"
        users_text += f"    <b>ID:</b> <code>{user_id_info}</code>\n"
        users_text += f"    <b>Status:</b> {status}\n"
        users_text += f"    <b>Joined:</b> {join_str}\n\n"

    # Summary statistics
    users_text += f"{'='*40}\n"
    users_text += f"<b>📊 Summary:</b>\n"
    users_text += f"• <b>Premium Users:</b> {pro_count + plus_count}\n"
    users_text += f"• <b>Free Users:</b> {free_count}\n"
    users_text += f"• <b>Total:</b> {len(all_users)} users\n\n"

    # Generate pagination buttons
    buttons = []
    nav_row = []

    # First and Previous buttons
    if page > 1:
        if page > 2:
            nav_row.append(InlineKeyboardButton('⏪ First', callback_data='users_list_1'))
        nav_row.append(InlineKeyboardButton('◀️ Previous', callback_data=f'users_list_{page-1}'))

    # Current page indicator
    nav_row.append(InlineKeyboardButton(f'• {page}/{total_pages} •', callback_data='users_current'))

    # Next and Last buttons
    if page < total_pages:
        nav_row.append(InlineKeyboardButton('Next ▶️', callback_data=f'users_list_{page+1}'))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton('Last ⏩', callback_data=f'users_list_{total_pages}'))

    if nav_row:
        buttons.append(nav_row)

    # Quick jump buttons (show nearby pages)
    if total_pages > 5:
        jump_row = []
        start_jump = max(1, page - 2)
        end_jump = min(total_pages, page + 2)

        for p in range(start_jump, end_jump + 1):
            if p != page:
                jump_row.append(InlineKeyboardButton(str(p), callback_data=f'users_list_{p}'))

        if jump_row:
            buttons.append(jump_row)

    # Action buttons
    buttons.extend([
        [
            InlineKeyboardButton('🔄 Refresh', callback_data=f'users_list_{page}'),
            InlineKeyboardButton('💎 Premium Only', callback_data='admin_premium_users')
        ],
        [
            InlineKeyboardButton('📈 User Stats', callback_data='admin_user_stats'),
            InlineKeyboardButton('🆓 Free Only', callback_data='admin_free_users')
        ],
        [
            InlineKeyboardButton('🔙 Admin Menu', callback_data='admin_commands')
        ]
    ])

    return users_text, buttons

# /users command for admins to get list of all registered users
# /users command removed - now handled by python-telegram-bot in ptb_commands.py

# Enhanced callback handlers for user list pagination
@Client.on_callback_query(filters.regex(r'^users_list_(\d+)$'))
async def users_list_callback(client, callback_query):
    user_id = callback_query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)

    try:
        page = int(callback_query.data.split('_')[2])

        # Generate users list for the requested page
        users_text, buttons = await generate_users_list(page)

        await callback_query.message.edit_text(
            text=users_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        await callback_query.answer(f"📄 Page {page}")

    except Exception as e:
        logger.error(f"Error in users list callback: {e}", exc_info=True)
        await callback_query.answer("❌ Error loading page!", show_alert=True)

@Client.on_callback_query(filters.regex(r'^users_current$'))
async def users_current_callback(client, callback_query):
    """Handle current page indicator click"""
    await callback_query.answer("📍 Current page", show_alert=False)

@Client.on_callback_query(filters.regex(r'^admin_free_users$'))
async def admin_free_users_callback(client, callback_query):
    user_id = callback_query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)

    try:
        # Get all users and filter free users
        all_users = await db.get_all_users()
        free_users = []

        for user_info in all_users:
            user_id_info = user_info.get('id')
            if not await db.is_premium_user(user_id_info):
                free_users.append(user_info)

        if not free_users:
            return await callback_query.message.edit_text(
                "<b>🆓 Free Users</b>\n\n<i>No free users found!</i>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_commands')]])
            )

        users_text = f"<b>🆓 Free Users Only</b>\n"
        users_text += f"<b>Total Free Users:</b> {len(free_users)}\n"
        users_text += f"{'='*30}\n\n"

        for i, user_info in enumerate(free_users[:20], 1):  # Show first 20 free users
            user_id_info = user_info.get('id', 'Unknown')
            user_name = user_info.get('name', 'Unknown')
            joined_date = user_info.get('joined_date', 'Unknown')

            # Format join date
            if isinstance(joined_date, datetime):
                join_str = joined_date.strftime('%d %b %Y')
            else:
                join_str = "Unknown"

            # Check usage
            usage = await db.get_monthly_usage(user_id_info)
            usage_count = usage.get('processes', 0)

            display_name = user_name[:20] + "..." if len(user_name) > 20 else user_name

            users_text += f"<b>{i:2d}.</b> {display_name}\n"
            users_text += f"     <b>ID:</b> <code>{user_id_info}</code>\n"
            users_text += f"     <b>Usage:</b> {usage_count}/2 processes\n"
            users_text += f"     <b>Joined:</b> {join_str}\n\n"

        if len(free_users) > 20:
            users_text += f"<i>... and {len(free_users) - 20} more free users</i>\n"

        buttons = [
            [InlineKeyboardButton('👥 All Users', callback_data='users_list_1')],
            [InlineKeyboardButton('🔙 Admin Menu', callback_data='admin_commands')]
        ]

        await callback_query.message.edit_text(
            text=users_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_user_stats$'))
async def admin_user_stats_callback(client, callback_query):
    user_id = callback_query.from_user.id

    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)

    try:
        # Get comprehensive user statistics
        all_users = await db.get_all_users()
        premium_users = await db.get_all_premium_users()

        from datetime import datetime, timedelta
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Count statistics
        total_users = len(all_users)
        total_premium = len(premium_users)
        total_free = total_users - total_premium

        # Count by plan type
        pro_users = len([p for p in premium_users if p.get('plan_type') == 'pro'])
        plus_users = len([p for p in premium_users if p.get('plan_type') == 'plus'])

        # Count by join date
        new_today = len([u for u in all_users if u.get('joined_date', datetime.min) >= today])
        new_week = len([u for u in all_users if u.get('joined_date', datetime.min) >= week_ago])
        new_month = len([u for u in all_users if u.get('joined_date', datetime.min) >= month_ago])

        # Revenue calculation
        estimated_revenue = (pro_users * 549) + (plus_users * 299)

        stats_text = f"""<b>📊 Comprehensive User Statistics</b>

<b>👥 User Base Overview:</b>
├ <b>Total Users:</b> {total_users:,}
├ <b>Premium Users:</b> {total_premium:,} ({total_premium/total_users*100:.1f}%)
└ <b>Free Users:</b> {total_free:,} ({total_free/total_users*100:.1f}%)

<b>💎 Premium Breakdown:</b>
├ <b>🔥 Pro Users:</b> {pro_users:,}
├ <b>✨ Plus Users:</b> {plus_users:,}
└ <b>💰 Est. Revenue:</b> ₹{estimated_revenue:,}

<b>📈 Growth Statistics:</b>
├ <b>New Today:</b> {new_today:,}
├ <b>New This Week:</b> {new_week:,}
└ <b>New This Month:</b> {new_month:,}

<b>📊 Conversion Rate:</b>
├ <b>Free to Premium:</b> {total_premium/total_users*100:.1f}%
├ <b>Pro Preference:</b> {pro_users/(pro_users+plus_users)*100 if (pro_users+plus_users) > 0 else 0:.1f}%
└ <b>Daily Avg Signups:</b> {new_month/30:.1f}

<b>💡 Business Insights:</b>
• Premium conversion rate is {'excellent' if total_premium/total_users > 0.15 else 'good' if total_premium/total_users > 0.1 else 'needs improvement'}
• {'Strong' if new_today > 5 else 'Moderate' if new_today > 2 else 'Low'} user acquisition today
• Monthly revenue trend: ₹{estimated_revenue:,}"""

        buttons = [
            [
                InlineKeyboardButton('👥 All Users', callback_data='users_list_1'),
                InlineKeyboardButton('💎 Premium Only', callback_data='admin_premium_users')
            ],
            [
                InlineKeyboardButton('🔄 Refresh Stats', callback_data='admin_user_stats'),
                InlineKeyboardButton('🔙 Admin Menu', callback_data='admin_commands')
            ]
        ]

        await callback_query.message.edit_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)


# Added /trial command handler
# Removed duplicate /trial handler - using the first one in this file instead
# @Client.on_message(filters.private & filters.command(['trial']))
# async def trial_command(client, message):
#     user_id = message.from_user.id
    user_name = message.from_user.first_name
    logger.info(f"Trial command requested by user {user_id} ({user_name})")

    try:
        # Check if user can use free trial
        can_trial = await db.can_use_trial(user_id)

        if not can_trial:
            await message.reply_text(
                "❌ You have already used your free trial this year!\n"
                "💎 Upgrade to Premium for unlimited access.",
                quote=True
            )
            return

        if await db.is_premium_user(user_id):
            await message.reply_text(
                "✅ You already have Premium access!\n"
                "No need for free trial - you have unlimited processes.",
                quote=True
            )
            return

        # Grant the free trial (add 1 extra process - total 2 for this month)
        trial_granted = await db.add_trial_processes(user_id, 1)

        if not trial_granted:
            await message.reply_text(
                "❌ You have already claimed your free trial this month!\n"
                "💎 Upgrade to Premium for unlimited access.",
                quote=True
            )
            return

        # Send notification to admins
        try:
            notify = NotificationManager(client)
            await notify.notify_free_trial_activity(
                user_id=user_id,
                action="activated free trial via command",
                remaining_usage=1
            )
        except Exception as notify_err:
            logger.error(f"Failed to send free trial notification: {notify_err}")

        # Send confirmation message to user
        await message.reply_text(
            text="<b>🎉 Free Trial Activated!</b>\n\n"
                 "<b>✅ You have received +1 additional process for this month!</b>\n\n"
                 "<b>📋 Your monthly allowance:</b>\n"
                 "• Base free plan: 1 process\n"
                 "• Trial bonus: +1 process\n"
                 "• <b>Total available: 2 processes</b>\n\n"
                 "<b>What you can do:</b>\n"
                 "• Use /forward to start forwarding messages\n"
                 "• Process two forwarding jobs this month\n\n"
                 "<b>💎 Want unlimited access?</b>\n"
                 "Upgrade to Premium:\n"
                 "• <b>Plus Plan:</b> ₹199/15d, ₹299/30d - Unlimited forwarding\n"
                 "• <b>Pro Plan:</b> ₹299/15d, ₹549/30d - Unlimited + FTM Mode + Priority support\n\n"
                 "<b>🗓️ Resets:</b> 1st of next month",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🚀 Start Forwarding', callback_data='settings#main')],
                [InlineKeyboardButton('💎 Upgrade to Premium', callback_data='premium_info')],
                [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
            ]),
            quote=True
        )

        logger.info(f"Free trial granted via command to user {user_id}")

    except Exception as e:
        logger.error(f"Error in trial command for user {user_id}: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred. Please try again.")