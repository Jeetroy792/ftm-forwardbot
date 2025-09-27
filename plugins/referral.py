"""
Enhanced Referral System Plugin
===============================

This plugin handles all referral system functionality including:
- /referral command with stats and buttons
- Referral code generation and tracking
- Auto-rewards: 15 referrals = Plus 30d, 30 referrals = Pro 15d
- 1-day Plus plan for referred users
- Comprehensive notifications
- Leaderboard and help system
- Callback handlers for referral actions

Enhanced referral system provides automatic rewards and notifications.
"""

import logging
from database import db
from config import Config
from translation import Translation
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from typing import List

# Setup logging
logger = logging.getLogger(__name__)

# /referral command
@Client.on_message(filters.private & filters.command(['referral']))
async def referral_command(client, message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    try:
        # Get referral stats
        referral_stats = await db.get_referral_stats(user_id)

        # Build referral message
        referral_text = f"""🔗 <b>Enhanced Referral System</b>

👤 <b>Your Referral Code:</b> <code>{referral_stats['referral_code']}</code>

📊 <b>Your Statistics:</b>
• ✅ <b>Completed Referrals:</b> {referral_stats['total_completed']}/30
• ⏳ <b>Pending Referrals:</b> {referral_stats['total_pending']}

🎁 <b>Reward Progress:</b>
• <b>Plus Plan (30d):</b> {min(referral_stats['total_completed'], 15)}/15 {"✅" if referral_stats['total_completed'] >= 15 else "⏳"}
• <b>Pro Plan (15d):</b> {min(referral_stats['total_completed'], 30)}/30 {"✅" if referral_stats['total_completed'] >= 30 else "⏳"}

🎯 <b>Next Milestone:</b> {_get_next_milestone(referral_stats['total_completed'])}

💡 <b>How it works:</b>
• Share your referral link with friends
• When they start the bot & join all channels = 1 completed referral
• They get 1 day Plus plan FREE instantly! 🎁
• You get rewards at milestones:
  ▫️ 15 referrals = Plus Plan (30 days) FREE
  ▫️ 30 referrals = Pro Plan (15 days) FREE

🔗 <b>Your Referral Link:</b>
<code>https://t.me/{(await client.get_me()).username}?start={referral_stats['referral_code']}</code>"""

        buttons = [
            [
                InlineKeyboardButton('📋 Copy Link', callback_data=f"copy_referral#{referral_stats['referral_code']}"),
                InlineKeyboardButton('🔄 Refresh Stats', callback_data='refresh_referral')
            ],
            [
                InlineKeyboardButton('📈 Leaderboard', callback_data='referral_leaderboard'),
                InlineKeyboardButton('👥 Referral List', callback_data='referral_list')
            ],
            [
                InlineKeyboardButton('ℹ️ Help', callback_data='referral_help'),
                InlineKeyboardButton('🏠 Main Menu', callback_data='back')
            ]
        ]

        await message.reply_text(
            text=referral_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )

        logger.info(f"Referral command sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error in referral command for user {user_id}: {e}", exc_info=True)
        await message.reply_text(
            "❌ An error occurred. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='back')]])
        )

def _get_next_milestone(completed):
    """Get next milestone text"""
    if completed < 15:
        return f"{15 - completed} more for Plus Plan (30 days)"
    elif completed < 30:
        return f"{30 - completed} more for Pro Plan (15 days)"
    else:
        return "All milestones achieved! 🎉"

# Referral system callback handlers
@Client.on_callback_query(filters.regex(r'^copy_referral#'))
async def copy_referral_callback(client, callback_query):
    try:
        referral_code = callback_query.data.split('#')[1]
        referral_link = f"https://t.me/{(await client.get_me()).username}?start={referral_code}"

        await callback_query.answer(
            f"✅ Referral link copied!\n{referral_link}",
            show_alert=True
        )
    except Exception as e:
        logger.error(f"Error copying referral link: {e}")
        await callback_query.answer("❌ Error copying link", show_alert=True)


@Client.on_callback_query(filters.regex(r'^refresh_referral$'))
async def refresh_referral_callback(client, callback_query):
    user_id = callback_query.from_user.id

    try:
        # Get updated referral stats
        referral_stats = await db.get_referral_stats(user_id)

        # Build referral message with unique timestamp to avoid MESSAGE_NOT_MODIFIED
        current_time = datetime.now().strftime("%H:%M:%S")

        referral_text = f"""🔗 <b>Enhanced Referral System</b>

👤 <b>Your Referral Code:</b> <code>{referral_stats['referral_code']}</code>

📊 <b>Your Statistics:</b>
• ✅ <b>Completed Referrals:</b> {referral_stats['total_completed']}/30
• ⏳ <b>Pending Referrals:</b> {referral_stats['total_pending']}

🎁 <b>Reward Progress:</b>
• <b>Plus Plan (30d):</b> {min(referral_stats['total_completed'], 15)}/15 {"✅" if referral_stats['total_completed'] >= 15 else "⏳"}
• <b>Pro Plan (15d):</b> {min(referral_stats['total_completed'], 30)}/30 {"✅" if referral_stats['total_completed'] >= 30 else "⏳"}

🎯 <b>Next Milestone:</b> {_get_next_milestone(referral_stats['total_completed'])}

💡 <b>How it works:</b>
• Share your referral link with friends
• When they start the bot & join all channels = 1 completed referral
• They get 1 day Plus plan FREE instantly! 🎁
• You get rewards at milestones:
  ▫️ 15 referrals = Plus Plan (30 days) FREE
  ▫️ 30 referrals = Pro Plan (15 days) FREE

🔗 <b>Your Referral Link:</b>
<code>https://t.me/{(await client.get_me()).username}?start={referral_stats['referral_code']}</code>

<i>Updated: {current_time}</i>"""

        buttons = [
            [
                InlineKeyboardButton('📋 Copy Link', callback_data=f"copy_referral#{referral_stats['referral_code']}"),
                InlineKeyboardButton('🔄 Refresh Stats', callback_data='refresh_referral')
            ],
            [
                InlineKeyboardButton('📈 Leaderboard', callback_data='referral_leaderboard'),
                InlineKeyboardButton('👥 Referral List', callback_data='referral_list')
            ],
            [
                InlineKeyboardButton('ℹ️ Help', callback_data='referral_help'),
                InlineKeyboardButton('🏠 Main Menu', callback_data='back')
            ]
        ]

        await callback_query.message.edit_text(
            text=referral_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        await callback_query.answer("✅ Stats refreshed!", show_alert=False)

    except Exception as e:
        logger.error(f"Error refreshing referral stats: {e}")
        await callback_query.answer("❌ Error refreshing stats", show_alert=True)


@Client.on_callback_query(filters.regex(r'^referral_leaderboard$'))
async def referral_leaderboard_callback(client, callback_query):
    try:
        # Get leaderboard
        leaderboard = await db.get_referral_leaderboard(10)

        leaderboard_text = "🏆 <b>Referral Leaderboard</b>\n\n"

        if leaderboard:
            for i, entry in enumerate(leaderboard, 1):
                user_id = entry['_id']
                referrals = entry['total_referrals']

                # Get user info
                try:
                    user = await db.get_user(user_id)
                    user_name = user['name'] if user else f"User {user_id}"
                except:
                    user_name = f"User {user_id}"

                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} <b>{user_name}</b>: {referrals} referrals\n"
        else:
            leaderboard_text += "No completed referrals yet. Be the first! 🚀"

        leaderboard_text += "\n💡 <b>Tip:</b> Share your referral link to climb the leaderboard!"

        buttons = [
            [InlineKeyboardButton('🔙 Back to Referrals', callback_data='refresh_referral')]
        ]

        await callback_query.message.edit_text(
            text=leaderboard_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error loading referral leaderboard: {e}")
        await callback_query.answer("❌ Error loading leaderboard", show_alert=True)


@Client.on_callback_query(filters.regex(r'^referral_help$'))
async def referral_help_callback(client, callback_query):
    help_text = """ℹ️ <b>Enhanced Referral System Help</b>

🎯 <b>How to Earn:</b>
1. Share your unique referral link with friends
2. When they click your link and start the bot = tracking begins
3. When they join ALL required channels = referral completed ✅
4. Your friend gets 1 day Plus plan FREE instantly! 🎁
5. You earn milestone rewards automatically!

🏆 <b>Milestone Rewards:</b>
• <b>15 Referrals:</b> Plus Plan (30 days) FREE
• <b>30 Referrals:</b> Pro Plan (15 days) FREE

🎁 <b>Instant Rewards:</b>
• Every referred friend gets 1 day Plus plan FREE
• Both you and your friend get notifications
• Progress tracked in real-time

🔗 <b>Where to Share:</b>
• Social media platforms
• Telegram groups/channels  
• WhatsApp/Discord
• With friends and family

⚡ <b>Requirements for Completed Referral:</b>
• Friend must use YOUR referral link
• Friend must start the bot 
• Friend must join ALL force subscribe channels
• No self-referrals allowed

🔄 <b>Automatic System:</b>
• Rewards granted instantly upon completion
• Notifications sent to both users
• Progress tracked automatically
• No manual claims needed

❓ <b>FAQ:</b>
• <b>Q:</b> When does my friend get their free plan?
• <b>A:</b> Immediately after joining all channels!

• <b>Q:</b> When do I get milestone rewards?
• <b>A:</b> Automatically when you reach 15/30 referrals

• <b>Q:</b> Can I refer myself?
• <b>A:</b> No, self-referrals are not allowed"""

    buttons = [
        [InlineKeyboardButton('🔙 Back to Referrals', callback_data='refresh_referral')]
    ]

    await callback_query.message.edit_text(
        text=help_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r'^referral_list$'))
async def referral_list_callback(client, callback_query):
    user_id = callback_query.from_user.id

    try:
        # Get all referrals for the current user
        referrals = await db.get_all_referrals(user_id)

        if not referrals:
            await callback_query.answer("You haven't referred anyone yet.", show_alert=True)
            return

        referral_list_text = "👥 <b>Your Referral List</b>\n\n"

        for referral in referrals:
            referred_user_id = referral['referred_user_id']
            completed = referral['completed']

            try:
                # Fetch user info from database
                referred_user_info = await db.get_user(referred_user_id)
                referred_user_name = referred_user_info.get('name', f"User {referred_user_id}")
            except Exception:
                referred_user_name = f"User {referred_user_id}"

            status = "✅ Completed" if completed else "⏳ Pending"
            referral_list_text += f"• {referred_user_name}: {status}\n"

            if not completed:
                referral_list_text += "  👉 Please remind them to complete the referral for mutual benefit!\n"

        buttons = [
            [InlineKeyboardButton('🔙 Back to Referrals', callback_data='refresh_referral')]
        ]

        await callback_query.message.edit_text(
            text=referral_list_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await callback_query.answer("Referral list loaded.", show_alert=False)

    except Exception as e:
        logger.error(f"Error loading referral list for user {user_id}: {e}", exc_info=True)
        await callback_query.answer("❌ Error loading referral list.", show_alert=True)