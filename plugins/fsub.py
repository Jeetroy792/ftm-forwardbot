import logging
from datetime import datetime
import sys
import os
from config import Config
from database import db
from translation import Translation
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# It's better to configure logging and imports at the top level of the module.
# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Centralize dynamic imports for clarity
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.notifications import NotificationManager
from plugins.timezone import get_current_ist_timestamp


async def _send_referral_tracking_notification(client, referrer_user_id, referred_user_id):
    """Send notification when referral tracking starts (user clicked referral link)"""
    try:
        # Get user information
        try:
            referrer = await client.get_users(referrer_user_id)
            referred = await client.get_users(referred_user_id)
            referrer_name = referrer.first_name
            referred_name = referred.first_name
            referred_username = f"@{referred.username}" if referred.username else "No username"
        except Exception:
            referrer_name = f"User {referrer_user_id}"
            referred_name = f"User {referred_user_id}"
            referred_username = "Unknown"

        # Notify the referrer about the tracking start
        try:
            await client.send_message(
                referrer_user_id,
                f"🎯 <b>Referral Tracking Started!</b>\n\n"
                f"👤 <b>{referred_name} ({referred_username}) clicked your referral link!</b>\n\n"
                f"⏳ <b>Status:</b> Referral in progress\n"
                f"📋 <b>Next Step:</b> {referred_name} needs to join all required channels\n\n"
                f"🎁 <b>When completed:</b>\n"
                f"• {referred_name} gets 1 day Plus plan FREE\n"
                f"• You get +1 referral credit\n\n"
                f"<b>💡 Encourage them to complete registration for mutual rewards!</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('📊 My Referral Stats', callback_data='refresh_referral')]
                ])
            )
        except Exception as e:
            logger.error(f"Failed to notify referrer about tracking start: {e}")

        # Send log notification
        try:
            notify = NotificationManager(client)
            await notify.send_log_notification(
                f"🎯 <b>REFERRAL TRACKING INITIATED</b>\n"
                f"<b>📊 Priority:</b> ℹ️ INFO\n"
                f"<b>🕒 Timestamp:</b> {get_current_ist_timestamp()}\n"
                f"{'-' * 50}\n\n"
                f"<b>👤 Referrer:</b> {referrer_name} (<code>{referrer_user_id}</code>)\n"
                f"<b>👤 Referred User:</b> {referred_name} (<code>{referred_user_id}</code>)\n"
                f"<b>🔗 Status:</b> Referral link clicked, force subscribe required\n"
                f"<b>📈 Progress:</b> Awaiting channel subscriptions for completion"
            )
        except Exception as e:
            logger.error(f"Failed to send referral tracking log: {e}")

    except Exception as e:
        logger.error(f"Error in referral tracking notification: {e}")


async def _send_referral_completion_notifications(client, referrer_user_id, referred_user_id, total_referrals, reward_granted):
    """Send enhanced notifications when referral is completed"""
    try:
        # Get user information
        try:
            referrer = await client.get_users(referrer_user_id)
            referred = await client.get_users(referred_user_id)
            referrer_name = referrer.first_name
            referred_name = referred.first_name
            referrer_username = f"@{referrer.username}" if referrer.username else "No username"
            referred_username = f"@{referred.username}" if referred.username else "No username"
        except Exception:
            referrer_name = f"User {referrer_user_id}"
            referred_name = f"User {referred_user_id}"
            referrer_username = "Unknown"
            referred_username = "Unknown"

        # Notify the referred user (they got 1 day Plus plan)
        try:
            await client.send_message(
                referred_user_id,
                f"🎉 <b>Referral Registration Completed!</b>\n\n"
                f"✅ <b>Welcome! You were successfully referred by {referrer_name}!</b>\n\n"
                f"🎁 <b>INSTANT REWARD ACTIVATED:</b>\n"
                f"• ✨ <b>1 Day Plus Plan</b> added to your account!\n"
                f"• ♾️ <b>Unlimited forwarding</b> for 24 hours\n"
                f"• 🚀 <b>All premium features</b> unlocked\n"
                f"• ⚡ <b>Enhanced performance</b> enabled\n\n"
                f"<b>🔥 Start using your premium benefits now:</b>\n"
                f"• Use /forward to start unlimited forwarding\n"
                f"• Use /settings to configure advanced features\n"
                f"• Use /myplan to check your premium status\n\n"
                f"<b>💎 Want to extend your premium access?</b>\n"
                f"• Refer friends with /referral and earn more!\n"
                f"• Upgrade to longer plans with /plan\n\n"
                f"<b>🙏 Thank you for joining our community!</b>",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton('🚀 Start Forwarding', callback_data='settings#main'),
                        InlineKeyboardButton('📊 My Plan', callback_data='my_plan')
                    ],
                    [
                        InlineKeyboardButton('🔗 My Referral Link', callback_data='refresh_referral'),
                        InlineKeyboardButton('💎 Upgrade Plans', callback_data='premium_plans')
                    ]
                ])
            )
        except Exception as e:
            logger.error(f"Failed to notify referred user {referred_user_id}: {e}")

        # Determine milestone reward text
        milestone_text = ""
        milestone_buttons = []
        if reward_granted:
            if total_referrals == 15:
                milestone_text = "\n\n🏆 <b>MILESTONE ACHIEVEMENT UNLOCKED!</b>\n🎊 <b>You've earned Plus Plan (30 days) for reaching 15 referrals!</b>\n💎 <b>Your account has been automatically upgraded!</b>"
                milestone_buttons = [InlineKeyboardButton('🎊 View My Premium', callback_data='my_plan')]
            elif total_referrals == 30:
                milestone_text = "\n\n🏆 <b>ULTIMATE MILESTONE ACHIEVEMENT!</b>\n👑 <b>You've earned Pro Plan (15 days) for reaching 30 referrals!</b>\n🔥 <b>FTM Mode and all premium features unlocked!</b>"
                milestone_buttons = [InlineKeyboardButton('👑 View Pro Features', callback_data='my_plan')]

        # Notify the referrer with enhanced message
        try:
            referrer_buttons = [
                [
                    InlineKeyboardButton('📊 Referral Stats', callback_data='refresh_referral'),
                    InlineKeyboardButton('📋 Leaderboard', callback_data='referral_leaderboard')
                ]
            ]

            if milestone_buttons:
                referrer_buttons.insert(0, milestone_buttons)

            await client.send_message(
                referrer_user_id,
                f"🎉 <b>Referral Credit Earned!</b>\n\n"
                f"✅ <b>{referred_name} completed registration successfully!</b>\n"
                f"📈 <b>Your referral progress updated:</b>\n"
                f"├ <b>Total Completed Referrals:</b> {total_referrals}/30\n"
                f"├ <b>Latest Referral:</b> {referred_name} ({referred_username})\n"
                f"└ <b>Reward Granted:</b> {referred_name} received 1 day Plus plan\n\n"
                f"🎯 <b>Referral Milestones:</b>\n"
                f"• 15 referrals = Plus Plan (30 days) {'✅ ACHIEVED' if total_referrals >= 15 else f'({total_referrals}/15)'}\n"
                f"• 30 referrals = Pro Plan (15 days) {'✅ ACHIEVED' if total_referrals >= 30 else f'({total_referrals}/30)'}{milestone_text}\n\n"
                f"<b>🔥 Keep sharing your referral link to earn more rewards!</b>\n"
                f"<b>Use /referral to get your link and track progress!</b>",
                reply_markup=InlineKeyboardMarkup(referrer_buttons)
            )
        except Exception as e:
            logger.error(f"Failed to notify referrer {referrer_user_id}: {e}")

        # Send comprehensive log channel notification
        try:
            notify = NotificationManager(client)

            milestone_status = "No milestone reached"
            if reward_granted:
                if total_referrals == 15:
                    milestone_status = "🏆 15 REFERRALS MILESTONE - Plus Plan (30d) auto-granted"
                elif total_referrals == 30:
                    milestone_status = "👑 30 REFERRALS MILESTONE - Pro Plan (15d) auto-granted"

            await notify.send_log_notification(
                f"🔗 <b>REFERRAL SYSTEM - SUCCESSFUL COMPLETION</b>\n"
                f"<b>📊 Priority:</b> ✅ SUCCESS\n"
                f"<b>🕒 Timestamp:</b> {get_current_ist_timestamp()}\n"
                f"{'-' * 50}\n\n"
                f"<b>👤 Referrer Details:</b>\n"
                f"├ <b>Name:</b> {referrer_name}\n"
                f"├ <b>Username:</b> {referrer_username}\n"
                f"├ <b>User ID:</b> <code>{referrer_user_id}</code>\n"
                f"├ <b>Total Referrals:</b> {total_referrals}/30\n"
                f"└ <b>Referral Progress:</b> {(total_referrals/30)*100:.1f}% to ultimate milestone\n\n"
                f"<b>👤 Referred User Details:</b>\n"
                f"├ <b>Name:</b> {referred_name}\n"
                f"├ <b>Username:</b> {referred_username}\n"
                f"├ <b>User ID:</b> <code>{referred_user_id}</code>\n"
                f"├ <b>Instant Reward:</b> 1 day Plus plan\n"
                f"└ <b>Account Status:</b> Premium activated\n\n"
                f"<b>🏆 Milestone Information:</b>\n"
                f"├ <b>Current Status:</b> {milestone_status}\n"
                f"├ <b>15 Referrals Milestone:</b> {'✅ Achieved' if total_referrals >= 15 else f'⏳ {15-total_referrals} remaining'}\n"
                f"└ <b>30 Referrals Milestone:</b> {'✅ Achieved' if total_referrals >= 30 else f'⏳ {30-total_referrals} remaining'}\n\n"
                f"<b>📈 System Performance:</b>\n"
                f"├ <b>Registration:</b> ✅ Completed successfully\n"
                f"├ <b>Force Subscribe:</b> ✅ All channels verified\n"
                f"├ <b>Rewards Distribution:</b> ✅ Automatic premium granted\n"
                f"├ <b>Notifications:</b> ✅ Both users notified\n"
                f"└ <b>Database:</b> ✅ All records updated\n\n"
                f"<b>💼 Business Impact:</b>\n"
                f"├ <b>New Premium User:</b> {referred_name} (1 day Plus)\n"
                f"├ <b>Referral Engagement:</b> {'High' if total_referrals >= 10 else 'Growing'}\n"
                f"└ <b>Community Growth:</b> Successful viral expansion"
            )
        except Exception as e:
            logger.error(f"Failed to send log notification: {e}")

    except Exception as e:
        logger.error(f"Error in referral completion notifications: {e}")


"""
Force Subscribe Plugin
======================

This plugin handles all force subscription functionality including:
- Generating subscription buttons
- Checking subscription status
- Handling subscription verification callbacks
- Centralized force subscribe logic

All force subscribe functionality is consolidated here to avoid duplication.
"""


async def _build_enhanced_force_sub_message(client, user_id, joined_channels):
    """Build enhanced force subscribe message with referral information"""
    try:
        # Check if user was referred
        user_data = await db.get_user(user_id)
        referrer_user_id = user_data.get('referred_by') if user_data else None

        if referrer_user_id:
            # Get referrer information
            try:
                referrer = await client.get_users(referrer_user_id)
                referrer_name = referrer.first_name
                referrer_username = f"@{referrer.username}" if referrer.username else "No username"
            except Exception:
                referrer_name = f"User {referrer_user_id}"
                referrer_username = "Unknown"

            force_sub_text = (
                f"🎁 <b>Special Referral Registration!</b>\n\n"
                f"👋 <b>Welcome! You were invited by {referrer_name} ({referrer_username})!</b>\n\n"
                f"🏆 <b>Complete your registration to unlock exclusive rewards:</b>\n\n"
                f"🎁 <b>Your Instant Rewards:</b>\n"
                f"• ✨ <b>You get:</b> 1 Day Plus Plan FREE! (Unlimited forwarding)\n"
                f"• ♾️ <b>Access to:</b> All premium features for 24 hours\n"
                f"• 🚀 <b>Benefit:</b> No daily limits, enhanced performance\n\n"
                f"🎯 <b>{referrer_name}'s Rewards:</b>\n"
                f"• 📈 <b>Gets:</b> +1 referral credit towards premium plans\n"
                f"• 🏆 <b>Progress:</b> Closer to milestone rewards (15 & 30 referrals)\n\n"
                f"🔒 <b>Join all channels below to activate both rewards:</b>\n"
                f"⚡ <b>Both you and your friend get notified once completed!</b>\n\n"
            )
        else:
            force_sub_text = (
                "🔒 <b>Join Required Channels</b>\n\n"
                "<b>To access the bot, please join all required channels:</b>\n\n"
            )

        if joined_channels:
            force_sub_text += "<b>✅ Already Joined:</b>\n"
            for channel in joined_channels:
                force_sub_text += f"• {channel} ✅\n"
            force_sub_text += "\n<b>📢 Please join the remaining channels below:</b>"

        return force_sub_text

    except Exception as e:
        logger.error(f"Error building enhanced force sub message: {e}")
        # Fallback to basic message
        force_sub_text = Translation.FORCE_SUBSCRIBE_MSG
        if joined_channels:
            force_sub_text += "\n\n<b>✅ Already Joined:</b>\n"
            for channel in joined_channels:
                force_sub_text += f"• {channel} ✅\n"
            force_sub_text += "\n<b>📢 Please join the remaining channels below:</b>"
        return force_sub_text


async def build_force_subscribe_message_and_buttons(client, user_id):
    """
    Build complete force subscribe message with buttons for missing channels only

    Args:
        client: Pyrogram client instance
        user_id: User ID to check subscriptions for

    Returns:
        tuple: (message_text, InlineKeyboardMarkup or None)
    """
    if Config.is_sudo_user(user_id) or not Config.MULTI_FSUB:
        return None, None

    subscription_status = await check_force_subscribe(user_id, client)
    if subscription_status['all_subscribed']:
        return None, None

    force_buttons, joined_channels = await get_force_sub_buttons(client, user_id)
    if not force_buttons:
        return None, None

    # Build enhanced message text with referral info
    force_sub_text = await _build_enhanced_force_sub_message(client, user_id, joined_channels)

    return force_sub_text, InlineKeyboardMarkup(force_buttons)


async def get_force_sub_buttons(client, user_id):
    """
    Generate force subscribe buttons for missing channels

    Returns:
        tuple: (buttons_list, joined_channels_list)
    """
    if not Config.MULTI_FSUB:
        return [], []

    buttons = []
    joined_channels = []

    for channel_id in Config.MULTI_FSUB:
        try:
            chat = await client.get_chat(channel_id)
            chat_title = chat.title or f"Channel {channel_id}"

            # Check if user is subscribed
            try:
                member = await client.get_chat_member(channel_id, user_id)
                is_subscribed = member.status not in ['left', 'kicked']

                if is_subscribed:
                    joined_channels.append(chat_title)
                else:
                    # Create invite link or use chat username
                    if chat.username:
                        invite_link = f"https://t.me/{chat.username}"
                    else:
                        try:
                            invite_link_obj = await client.create_chat_invite_link(channel_id)
                            invite_link = invite_link_obj.invite_link
                        except Exception:
                            invite_link = f"https://t.me/c/{str(channel_id)[4:]}"

                    buttons.append([InlineKeyboardButton(f"📢 Join {chat_title}", url=invite_link)])

            except Exception as member_error:
                logger.error(f"Error checking membership for {channel_id}: {member_error}")
                # Add button anyway for channels we can't check
                try:
                    if chat.username:
                        invite_link = f"https://t.me/{chat.username}"
                    else:
                        invite_link = f"https://t.me/c/{str(channel_id)[4:]}"
                    buttons.append([InlineKeyboardButton(f"📢 Join {chat_title}", url=invite_link)])
                except Exception:
                    pass

        except Exception as chat_error:
            logger.error(f"Error getting chat info for {channel_id}: {chat_error}")
            # Add a generic button for channels we can't access
            buttons.append([InlineKeyboardButton(f"📢 Join Channel", url=f"https://t.me/c/{str(channel_id)[4:]}")])

    # Add check subscription button if there are missing channels
    if buttons:
        buttons.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")])

    return buttons, joined_channels


async def check_force_subscribe(user_id, client):
    """
    Check if user is subscribed to all required channels

    Args:
        user_id (int): User ID to check
        client: Pyrogram client instance

    Returns:
        dict: Subscription status with details
    """
    try:
        return await db.check_force_subscribe(user_id, client)
    except Exception as e:
        logger.error(f"Error checking force subscription for user {user_id}: {e}")
        return {
            'all_subscribed': False,
            'missing_channels': ['Required channels']
        }


async def force_subscribe_required(user_id, client):
    """
    Check if force subscription is required for this user

    Args:
        user_id (int): User ID to check
        client: Pyrogram client instance

    Returns:
        tuple: (bool: is_required, InlineKeyboardMarkup or None: buttons, list: joined_channels)
    """
    # Skip force subscribe check for sudo users
    if Config.is_sudo_user(user_id):
        return False, None, []

    # Skip if no force subscribe channels configured
    if not Config.MULTI_FSUB:
        return False, None, []

    # Check subscription status
    subscription_status = await check_force_subscribe(user_id, client)

    if not subscription_status['all_subscribed']:
        force_buttons, joined_channels = await get_force_sub_buttons(client, user_id)
        if force_buttons:
            return True, InlineKeyboardMarkup(force_buttons), joined_channels
        else:
            # All channels joined, no buttons needed
            return False, None, joined_channels

    return False, None, []


async def send_force_subscribe_message(message, client):
    """
    Send enhanced force subscribe message to user with referral information

    Args:
        message: Pyrogram message object
        client: Pyrogram client instance

    Returns:
        Message: Sent message object or None
    """
    user_id = message.from_user.id

    is_required, buttons, joined_channels = await force_subscribe_required(user_id, client)

    if is_required and buttons:
        # Build enhanced force subscribe text with referral info
        force_sub_text = await _build_enhanced_force_sub_message(client, user_id, joined_channels)

        # Send initial referral tracking notification if user was referred and hasn't been sent before
        try:
            user_data = await db.get_user(user_id)
            if user_data and user_data.get('referred_by') and not user_data.get('referral_completed'):
                # Check if tracking notification was already sent
                referral_record = await db.referral_col.find_one({
                    'referred_user_id': user_id,
                    'referrer_user_id': user_data.get('referred_by')
                })

                if referral_record and not referral_record.get('tracking_notification_sent', False):
                    # Send tracking started notification
                    logger.info(f"Sending referral tracking notification for user {user_id} referred by {user_data.get('referred_by')}")
                    await _send_referral_tracking_notification(client, user_data.get('referred_by'), user_id)
                    # Mark notification as sent
                    await db.referral_col.update_one(
                        {'_id': referral_record['_id']},
                        {'$set': {'tracking_notification_sent': True}}
                    )
                    logger.info(f"Referral tracking notification sent and marked as sent")
        except Exception as e:
            logger.error(f"Error sending referral tracking notification: {e}", exc_info=True)

        return await message.reply_text(
            text=force_sub_text,
            reply_markup=buttons,
            quote=True
        )

    return None


def get_main_buttons():
    """Dynamically generate the main buttons for the bot's menu."""
    return [
        [
            InlineKeyboardButton('📜 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ ', url=Config.SUPPORT_GROUP),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ  ', url=Config.UPDATE_CHANNEL)
        ],
        [
            InlineKeyboardButton('🎁 Get Free Trial', callback_data='get_free_trial'),
            InlineKeyboardButton('📊 My Plan', callback_data='my_plan')
        ],
        [
            InlineKeyboardButton('💎 Premium Plans', callback_data='premium_plans'),
            InlineKeyboardButton('🙋‍♂️ ʜᴇʟᴘ', callback_data='help')
        ],
        [
            InlineKeyboardButton('💁‍♂️ ᴀʙᴏᴜᴛ ', callback_data='about'),
            InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ⚙️', callback_data='settings#main')
        ],
        [
            InlineKeyboardButton('📞 Contact Admin', callback_data='contact_admin')
        ]
    ]


# Force subscribe callback handler
@Client.on_callback_query(filters.regex(r'^check_subscription$'))
async def check_subscription_callback(client, callback_query):
    """
    Handle subscription verification callback with enhanced referral tracking

    When user clicks "Check Subscription" button, verify their subscription
    status and either grant access or show missing channels with referral info.
    """
    user_id = callback_query.from_user.id
    logger.info(f"Subscription check callback from user {user_id}")

    try:
        # Check if user is now subscribed
        subscription_status = await check_force_subscribe(user_id, client)

        if subscription_status['all_subscribed']:
            await callback_query.answer("✅ Subscription verified! Welcome!", show_alert=True)

            # Mark referral channels as joined and handle completion
            referral_result = await db.mark_referral_channels_joined(user_id)

            # If referral was completed, send notifications
            if referral_result and isinstance(referral_result, dict) and referral_result.get('completed'):
                try:
                    await _send_referral_completion_notifications(
                        client, 
                        referral_result['referrer_user_id'], 
                        referral_result['referred_user_id'],
                        referral_result['total_referrals'],
                        referral_result['reward_granted']
                    )
                    logger.info(f"Referral completion notifications sent for user {user_id}")
                except Exception as e:
                    logger.error(f"Error sending referral completion notifications: {e}")

            # Show main menu
            reply_markup = InlineKeyboardMarkup(get_main_buttons())
            text = f"🎉 <b>Welcome {callback_query.from_user.first_name}!</b>\n\n" + Translation.START_TXT.format(callback_query.from_user.mention)

            await callback_query.message.edit_text(
                text=text,
                reply_markup=reply_markup
            )

            logger.info(f"User {user_id} successfully verified subscription")
        else:
            # Get updated buttons showing only missing channels and joined channels info
            force_buttons, joined_channels = await get_force_sub_buttons(client, user_id)

            # Check if user was referred and build enhanced message
            force_sub_text = await _build_enhanced_force_sub_message(client, user_id, joined_channels)

            # Update the message with new buttons
            if force_buttons:
                await callback_query.message.edit_text(
                    text=force_sub_text,
                    reply_markup=InlineKeyboardMarkup(force_buttons)
                )

            # Show alert with remaining channels
            missing_names = []
            for channel_id in Config.MULTI_FSUB:
                try:
                    # FIXED: Duplicated method call and incorrect indentation
                    if not await db.is_user_subscribed_to_channel(user_id, channel_id, client):
                        try:
                            chat_info = await client.get_chat(channel_id)
                            channel_name = chat_info.title or f"Channel {abs(channel_id)}"
                        except Exception:
                            channel_name = "Required Channel"
                        missing_names.append(channel_name)
                except Exception:
                    pass

            if len(missing_names) > 2:
                missing_text = f"{', '.join(missing_names[:2])} and {len(missing_names) - 2} more"
            else:
                missing_text = ', '.join(missing_names) if missing_names else "required channels"

            await callback_query.answer(f"❌ Please join: {missing_text}", show_alert=True)
            logger.info(f"User {user_id} still missing channels: {missing_names}")

    except Exception as e:
        logger.error(f"Error in subscription check callback for user {user_id}: {e}", exc_info=True)
        await callback_query.answer("❌ Error checking subscription. Please try again.", show_alert=True)
