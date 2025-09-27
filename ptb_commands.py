#!/usr/bin/env python3
"""
Python-Telegram-Bot handlers for specific commands that weren't working with Pyrogram.
This file handles: /info, /reset, /users, /resetall
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest, Forbidden

# Import existing modules
from database import db
from config import Config
from plugins.timezone import display_joined_date, display_expiry_date, time_until_expiry

# Setup logging and reduce verbose HTTP logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce httpx and telegram library verbosity
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

async def info_command(update: Update, context: CallbackContext) -> None:
    """Handle /info command"""
    if not update.effective_user or not update.message:
        return
    
    user = update.effective_user
    user_id = user.id
    
    print(f"PTB DEBUG: /info command triggered by user {user_id}")
    logger.info(f"PTB Info command from user {user_id}")
    
    try:
        # Get user information
        premium_info = await db.get_premium_user_details(user_id)
        daily_usage = await db.get_daily_usage(user_id)
        monthly_usage = await db.get_monthly_usage(user_id)
        user_data = await db.get_user(user_id)

        # Format join date
        join_date = user_data.get('joined_date', datetime.utcnow()) if user_data else datetime.utcnow()
        join_date_str = display_joined_date(join_date)

        # Build user info text
        info_text = f"<b>👤 Your Account Information</b>\n\n"
        info_text += f"<b>📋 Basic Details:</b>\n"
        info_text += f"• <b>Name:</b> {user.first_name}"
        if user.last_name:
            info_text += f" {user.last_name}"
        info_text += f"\n• <b>Username:</b> @{user.username}" if user.username else "\n• <b>Username:</b> Not set"
        info_text += f"\n• <b>User ID:</b> <code>{user_id}</code>"
        info_text += f"\n• <b>Joined:</b> {join_date_str}\n\n"

        # Subscription status
        if premium_info:
            plan_type = premium_info.get('plan_type', 'unknown').upper()
            expires_at = premium_info.get('expires_at', 'Unknown')
            if isinstance(expires_at, datetime):
                expires_at_str = display_expiry_date(expires_at)
                time_remaining = time_until_expiry(expires_at)
            else:
                expires_at_str = str(expires_at)
                time_remaining = "Unknown"

            info_text += f"<b>💎 Subscription Status:</b>\n"
            info_text += f"• <b>Plan:</b> {plan_type} Plan ✅\n"
            info_text += f"• <b>Expires:</b> {expires_at_str}\n"
            info_text += f"• <b>Time Left:</b> {time_remaining}\n\n"
        else:
            info_text += f"<b>🆓 Subscription Status:</b>\n"
            info_text += f"• <b>Plan:</b> Free User\n"
            info_text += f"• <b>Limit:</b> 1 process per month\n\n"

        # Usage statistics
        info_text += f"<b>📊 Usage Statistics:</b>\n"
        info_text += f"• <b>This Month:</b> {monthly_usage.get('processes', 0)} processes\n"
        info_text += f"• <b>Today:</b> {daily_usage.get('processes', 0)} processes\n"

        # Get forwarding limit
        limit = await db.get_forwarding_limit(user_id)
        if limit == -1:
            info_text += f"• <b>Limit:</b> Unlimited processes ♾️\n\n"
        else:
            remaining = max(0, limit - monthly_usage.get('processes', 0))
            info_text += f"• <b>Monthly Limit:</b> {limit} processes\n"
            info_text += f"• <b>Remaining:</b> {remaining} processes\n\n"

        info_text += f"<b>Use /myplan for subscription details and upgrade options.</b>"

        keyboard = [
            [InlineKeyboardButton('💎 My Plan', callback_data='my_plan')],
            [InlineKeyboardButton('⚙️ Settings', callback_data='settings#main')],
            [InlineKeyboardButton('🔙 Main Menu', callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in PTB info command for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred while fetching your information. Please try again.")

async def reset_command(update: Update, context: CallbackContext) -> None:
    """Handle /reset command"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    print(f"PTB DEBUG: /reset command triggered by user {user_id}")
    logger.info(f"PTB Reset command triggered by user {user_id}")
    
    try:
        # Confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton('✅ Yes, Reset Everything', callback_data=f'confirm_reset_{user_id}'),
                InlineKeyboardButton('❌ Cancel', callback_data='cancel_reset')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text="<b>⚠️ RESET CONFIRMATION</b>\n\n"
                 "<b>This will permanently delete:</b>\n"
                 "• All your bot configurations\n"
                 "• All saved channels\n"
                 "• All custom settings\n"
                 "• Caption and button settings\n"
                 "• Filter preferences\n"
                 "• Database connections\n\n"
                 "<b>❗ This action cannot be undone!</b>\n\n"
                 "<b>Are you sure you want to continue?</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in PTB reset command for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def users_command(update: Update, context: CallbackContext) -> None:
    """Handle /users command - COMPREHENSIVE admin dashboard with ALL possible details"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    print(f"PTB DEBUG: /users command triggered by user {user_id}")
    logger.info(f"PTB Users command from admin {user_id}")

    if not Config.is_sudo_user(user_id):
        if update.message:
            await update.message.reply_text("❌ You don't have permission to use this command!")
        return

    try:
        # Parse page number from command arguments
        page = 1
        if context.args and len(context.args) > 0:
            try:
                page = max(1, int(context.args[0]))
            except ValueError:
                page = 1
        
        # Get all users from database
        all_users = await db.get_all_users()
        
        if not all_users:
            if update.message:
                await update.message.reply_text("📋 No registered users found.")
            return

        # COMPREHENSIVE STATISTICS - EVERYTHING
        total_users = len(all_users)
        premium_count = 0
        free_count = 0
        banned_count = 0
        active_today = 0
        active_week = 0
        active_month = 0
        total_revenue = 0.0
        total_referrals = 0
        sudo_users = 0
        trial_users = 0
        ftm_users = 0
        alpha_users = 0
        
        # Plan type counts
        free_plan_count = 0
        plus_plan_count = 0
        pro_plan_count = 0
        
        # Revenue tracking
        revenue_this_month = 0.0
        revenue_today = 0.0
        
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Comprehensive analysis of ALL users
        user_details_map = {}
        all_referral_data = []
        
        for user_info in all_users:
            user_id_info = user_info.get('id', 'Unknown')
            joined_date = user_info.get('joined_date', today)
            ban_status = user_info.get('ban_status', {})
            
            # Get COMPREHENSIVE user data
            premium_info = await db.get_premium_user_details(user_id_info)
            configs = await db.get_configs(user_id_info)
            monthly_usage = await db.get_monthly_usage(user_id_info)
            daily_usage = await db.get_daily_usage(user_id_info)
            trial_status = await db.get_trial_status(user_id_info)
            referral_stats = await db.get_referral_stats(user_id_info)
            
            user_details_map[user_id_info] = {
                'info': user_info,
                'premium': premium_info,
                'configs': configs,
                'monthly_usage': monthly_usage,
                'daily_usage': daily_usage,
                'trial': trial_status,
                'referrals': referral_stats,
                'ban_status': ban_status
            }
            
            # PREMIUM STATUS ANALYSIS
            if premium_info:
                premium_count += 1
                plan_type = premium_info.get('plan_type', 'unknown')
                amount_paid = premium_info.get('amount_paid', 0)
                
                # Plan counting
                if plan_type == 'plus':
                    plus_plan_count += 1
                elif plan_type == 'pro':
                    pro_plan_count += 1
                    
                # Sudo users
                if premium_info.get('is_sudo_lifetime'):
                    sudo_users += 1
                
                # Revenue calculation
                if isinstance(amount_paid, (int, float)) and amount_paid > 0:
                    total_revenue += float(amount_paid)
                    
                    # Time-based revenue
                    subscribed_at = premium_info.get('subscribed_at')
                    if isinstance(subscribed_at, datetime):
                        if subscribed_at >= today:
                            revenue_today += float(amount_paid)
                        if subscribed_at >= month_ago:
                            revenue_this_month += float(amount_paid)
            else:
                free_count += 1
                free_plan_count += 1
                
            # BAN STATUS
            if ban_status.get('is_banned', False):
                banned_count += 1
                
            # TRIAL STATUS
            if trial_status.get('activated', False):
                trial_users += 1
                
            # SPECIAL FEATURES
            if configs.get('ftm_mode', False):
                ftm_users += 1
            if configs.get('ftm_alpha_mode', False):
                alpha_users += 1
                
            # REFERRAL DATA
            if user_info.get('referral_code'):
                ref_count = referral_stats.get('total_referrals', 0)
                total_referrals += ref_count
                if ref_count > 0:
                    all_referral_data.append({
                        'user_id': user_id_info,
                        'name': user_info.get('name', 'Unknown'),
                        'code': user_info.get('referral_code'),
                        'count': ref_count
                    })
                
            # ACTIVITY ANALYSIS (join date based)
            if isinstance(joined_date, datetime):
                if joined_date >= today:
                    active_today += 1
                if joined_date >= week_ago:
                    active_week += 1
                if joined_date >= month_ago:
                    active_month += 1

        # REFERRAL LEADERBOARD (Top 10)
        referral_leaderboard = sorted(all_referral_data, key=lambda x: x['count'], reverse=True)[:10]
        
        # PAGINATION SETUP
        users_per_page = 8
        total_pages = max(1, (total_users + users_per_page - 1) // users_per_page)
        page = min(page, total_pages)
        
        start_idx = (page - 1) * users_per_page
        end_idx = min(start_idx + users_per_page, total_users)
        
        sorted_users = sorted(all_users, key=lambda x: x.get('joined_date', datetime.min), reverse=True)
        page_users = sorted_users[start_idx:end_idx]

        # BUILD COMPREHENSIVE DASHBOARD
        dashboard_text = (
            f"💎 <b>ULTIMATE USER MANAGEMENT DASHBOARD</b>\n"
            f"{'='*50}\n\n"
            
            f"📊 <b>CORE STATISTICS:</b>\n"
            f"├ 👥 <b>Total Users:</b> {total_users:,}\n"
            f"├ 💎 <b>Premium Users:</b> {premium_count} ({premium_count/total_users*100:.1f}%)\n"
            f"├ 🆓 <b>Free Users:</b> {free_count} ({free_count/total_users*100:.1f}%)\n"
            f"├ 🚫 <b>Banned Users:</b> {banned_count} ({banned_count/total_users*100:.1f}%)\n"
            f"├ 👑 <b>Sudo Users:</b> {sudo_users}\n"
            f"└ 🎯 <b>Trial Users:</b> {trial_users}\n\n"
            
            f"💰 <b>REVENUE ANALYSIS:</b>\n"
            f"├ 💸 <b>Total Revenue:</b> ₹{total_revenue:,.2f}\n"
            f"├ 📅 <b>This Month:</b> ₹{revenue_this_month:,.2f}\n"
            f"├ 🆕 <b>Today:</b> ₹{revenue_today:,.2f}\n"
            f"└ 💡 <b>Avg per User:</b> ₹{total_revenue/premium_count if premium_count > 0 else 0:,.2f}\n\n"
            
            f"📈 <b>PLAN DISTRIBUTION:</b>\n"
            f"├ 🆓 <b>Free:</b> {free_plan_count} users\n"
            f"├ ➕ <b>Plus:</b> {plus_plan_count} users\n"
            f"└ 🔥 <b>Pro:</b> {pro_plan_count} users\n\n"
            
            f"🔗 <b>REFERRAL SYSTEM:</b>\n"
            f"├ 🎁 <b>Total Referrals:</b> {total_referrals}\n"
            f"├ 👤 <b>Referring Users:</b> {len([r for r in all_referral_data if r['count'] > 0])}\n"
            f"└ 📊 <b>Avg Referrals:</b> {total_referrals/len(all_referral_data) if all_referral_data else 0:.1f}\n\n"
            
            f"⚡ <b>SPECIAL FEATURES:</b>\n"
            f"├ 🚀 <b>FTM Delta Users:</b> {ftm_users}\n"
            f"└ 🎯 <b>FTM Alpha Users:</b> {alpha_users}\n\n"
            
            f"📅 <b>ACTIVITY BREAKDOWN:</b>\n"
            f"├ 🆕 <b>Joined Today:</b> {active_today}\n"
            f"├ 📊 <b>This Week:</b> {active_week}\n"
            f"└ 📈 <b>This Month:</b> {active_month}\n\n"
        )
        
        # REFERRAL LEADERBOARD
        if referral_leaderboard:
            dashboard_text += f"🏆 <b>REFERRAL LEADERBOARD:</b>\n"
            for i, ref_data in enumerate(referral_leaderboard, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                name = ref_data['name'][:15] + "..." if len(ref_data['name']) > 15 else ref_data['name']
                dashboard_text += f"{medal} <code>{ref_data['user_id']}</code> • {name} • {ref_data['count']} refs\n"
            dashboard_text += "\n"
        
        dashboard_text += f"📄 <b>PAGE {page} of {total_pages}</b> (Users {start_idx + 1}-{end_idx})\n"
        dashboard_text += f"{'='*50}\n\n"
        
        # DETAILED USER LIST FOR CURRENT PAGE
        for i, user_info in enumerate(page_users, start=start_idx + 1):
            user_id_info = user_info.get('id', 'Unknown')
            details = user_details_map.get(user_id_info, {})
            
            user_name = user_info.get('name', 'Unknown')
            joined_date = user_info.get('joined_date', 'Unknown')
            premium_info = details.get('premium')
            configs = details.get('configs', {})
            monthly_usage = details.get('monthly_usage', {})
            ban_status = details.get('ban_status', {})
            referrals = details.get('referrals', {})
            
            # Status icons
            icons = []
            if premium_info:
                plan = premium_info.get('plan_type', 'unknown').upper()
                if premium_info.get('is_sudo_lifetime'):
                    icons.append("👑")
                else:
                    icons.append("💎")
                icons.append(f"[{plan}]")
            else:
                icons.append("🆓")
                
            if ban_status.get('is_banned'):
                icons.append("🚫")
            if user_info.get('referred_by'):
                icons.append("🔗")
            if configs.get('ftm_mode'):
                icons.append("⚡")
            if configs.get('ftm_alpha_mode'):
                icons.append("🚀")
                
            # Date formatting
            if isinstance(joined_date, datetime):
                days_ago = (datetime.utcnow() - joined_date).days
                date_str = joined_date.strftime("%d/%m/%Y")
                if days_ago == 0:
                    date_str += " (Today)"
                elif days_ago < 7:
                    date_str += f" ({days_ago}d ago)"
            else:
                date_str = "N/A"
                
            name_display = user_name[:20] + "..." if len(str(user_name)) > 20 else user_name
            
            dashboard_text += f"<b>#{i:02d}. {' '.join(icons)}</b>\n"
            dashboard_text += f"├ 👤 <b>{name_display}</b> • ID: <code>{user_id_info}</code>\n"
            dashboard_text += f"├ 📅 Joined: {date_str}\n"
            
            # Premium details
            if premium_info:
                amount = premium_info.get('amount_paid', 0)
                expires = premium_info.get('expires_at')
                if isinstance(expires, datetime) and not premium_info.get('is_sudo_lifetime'):
                    days_left = max(0, (expires - datetime.utcnow()).days)
                    dashboard_text += f"├ 💎 Premium: {plan} (₹{amount}, {days_left}d left)\n"
                elif premium_info.get('is_sudo_lifetime'):
                    dashboard_text += f"├ 👑 Premium: Lifetime Sudo\n"
                else:
                    dashboard_text += f"├ 💎 Premium: {plan} (₹{amount})\n"
            
            # Usage & Referrals
            processes = monthly_usage.get('processes', 0)
            ref_count = referrals.get('total_referrals', 0)
            ref_code = user_info.get('referral_code', 'None')
            
            dashboard_text += f"├ 📊 Usage: {processes} processes this month\n"
            if ref_count > 0 or ref_code != 'None':
                dashboard_text += f"├ 🎁 Referrals: {ref_count} users • Code: {ref_code}\n"
            
            # Ban status
            if ban_status.get('is_banned'):
                dashboard_text += f"└ 🚫 BANNED: {ban_status.get('ban_reason', 'No reason')}\n"
            else:
                dashboard_text += f"└ ✅ Status: Active\n"
            
            dashboard_text += "\n"
        
        # NAVIGATION BUTTONS
        keyboard = []
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="users_current_page"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
        
        keyboard.append(nav_buttons)
        
        # Action buttons
        action_row1 = [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"users_page_{page}"),
            InlineKeyboardButton("📊 Revenue", callback_data="users_revenue"),
        ]
        action_row2 = [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="users_leaderboard"),
            InlineKeyboardButton("📈 Analytics", callback_data="users_analytics")
        ]
        
        keyboard.append(action_row1)
        keyboard.append(action_row2)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Footer
        dashboard_text += f"💡 <b>Commands:</b> /users [page] • /broadcast • /users_detailed\n"
        dashboard_text += f"🕐 <b>Updated:</b> {datetime.utcnow().strftime('%H:%M:%S UTC')}\n"
        dashboard_text += f"📱 <b>Use buttons below for navigation and detailed analytics</b>"

        await update.message.reply_text(
            text=dashboard_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in PTB users command for admin {user_id}: {e}", exc_info=True)
        if update.message:
            await update.message.reply_text("❌ An error occurred while fetching comprehensive users data. Please try again.")

async def users_detailed_command(update: Update, context: CallbackContext) -> None:
    """Handle /users_detailed command - comprehensive user analysis with pagination"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    print(f"PTB DEBUG: /users_detailed command triggered by user {user_id}")
    logger.info(f"PTB Users detailed command from admin {user_id}")

    if not Config.is_sudo_user(user_id):
        if update.message:
            await update.message.reply_text("❌ You don't have permission to use this command!")
        return

    try:
        # Parse page number from command arguments
        page = 1
        if context.args and len(context.args) > 0:
            try:
                page = max(1, int(context.args[0]))
            except ValueError:
                page = 1
        
        # Get all users from database
        all_users = await db.get_all_users()
        
        if not all_users:
            if update.message:
                await update.message.reply_text("📋 No registered users found.")
            return

        # Pagination settings
        users_per_page = 8
        total_users = len(all_users)
        total_pages = max(1, (total_users + users_per_page - 1) // users_per_page)
        page = min(page, total_pages)  # Ensure page doesn't exceed total pages
        
        start_idx = (page - 1) * users_per_page
        end_idx = min(start_idx + users_per_page, total_users)
        
        # Sort users by join date (newest first)
        from datetime import datetime as dt
        sorted_users = sorted(all_users, key=lambda x: x.get('joined_date', dt.min), reverse=True)
        page_users = sorted_users[start_idx:end_idx]

        # Calculate comprehensive statistics
        premium_count = 0
        free_count = 0
        banned_count = 0
        referred_count = 0
        trial_users = 0
        active_today = 0
        active_this_week = 0
        active_this_month = 0
        
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Gather comprehensive stats
        for user_info in all_users:
            user_id_info = user_info.get('id', 'Unknown')
            joined_date = user_info.get('joined_date', today)
            
            # Premium status check
            premium_info = await db.get_premium_user_details(user_id_info)
            if premium_info:
                premium_count += 1
            else:
                free_count += 1
                
            # Ban status check
            ban_status = user_info.get('ban_status', {})
            if ban_status.get('is_banned', False):
                banned_count += 1
                
            # Referral check
            if user_info.get('referred_by'):
                referred_count += 1
                
            # Trial check
            trial_status = await db.get_trial_status(user_id_info)
            if trial_status.get('activated', False):
                trial_users += 1
            
            # Activity checks
            if isinstance(joined_date, datetime):
                if joined_date >= today:
                    active_today += 1
                if joined_date >= week_ago:
                    active_this_week += 1
                if joined_date >= month_ago:
                    active_this_month += 1

        # Build comprehensive header
        header_text = (
            f"📊 <b>COMPREHENSIVE USER ANALYSIS</b>\n"
            f"═══════════════════════════════════\n\n"
            f"📈 <b>OVERVIEW STATISTICS:</b>\n"
            f"👥 <b>Total Users:</b> {total_users:,}\n"
            f"💎 <b>Premium Users:</b> {premium_count} ({premium_count/total_users*100:.1f}%)\n"
            f"🆓 <b>Free Users:</b> {free_count} ({free_count/total_users*100:.1f}%)\n"
            f"🚫 <b>Banned Users:</b> {banned_count} ({banned_count/total_users*100:.1f}%)\n"
            f"🔗 <b>Referred Users:</b> {referred_count} ({referred_count/total_users*100:.1f}%)\n"
            f"🎯 <b>Trial Users:</b> {trial_users} ({trial_users/total_users*100:.1f}%)\n\n"
            f"📅 <b>ACTIVITY BREAKDOWN:</b>\n"
            f"🆕 <b>Joined Today:</b> {active_today}\n"
            f"📊 <b>Joined This Week:</b> {active_this_week}\n"
            f"📈 <b>Joined This Month:</b> {active_this_month}\n\n"
            f"📄 <b>PAGE {page} of {total_pages}</b> (Users {start_idx + 1}-{end_idx})\n"
            f"═══════════════════════════════════\n\n"
        )
        
        # Build detailed user information
        detailed_text = ""
        for i, user_info in enumerate(page_users, start=start_idx + 1):
            user_id_info = user_info.get('id', 'Unknown')
            user_name = user_info.get('name', 'Unknown')
            joined_date = user_info.get('joined_date', 'Unknown')
            
            # Get comprehensive user data
            premium_info = await db.get_premium_user_details(user_id_info)
            ban_status = user_info.get('ban_status', {})
            configs = await db.get_configs(user_id_info)
            monthly_usage = await db.get_monthly_usage(user_id_info)
            daily_usage = await db.get_daily_usage(user_id_info)
            trial_status = await db.get_trial_status(user_id_info)
            referral_stats = await db.get_referral_stats(user_id_info)
            
            # Format user header
            status_icons = []
            plan_type = "FREE"  # Default value
            if premium_info:
                plan_type = premium_info.get('plan_type', 'unknown').upper()
                if premium_info.get('is_sudo_lifetime'):
                    status_icons.append("👑")
                else:
                    status_icons.append("💎")
                status_icons.append(f"[{plan_type}]")
            else:
                status_icons.append("🆓")
                
            if ban_status.get('is_banned', False):
                status_icons.append("🚫")
                
            if user_info.get('referred_by'):
                status_icons.append("🔗")
                
            if trial_status.get('activated', False):
                status_icons.append("🎯")
                
            if configs.get('ftm_mode', False):
                status_icons.append("⚡")
                
            if configs.get('ftm_alpha_mode', False):
                status_icons.append("🚀")
            
            # Format join date
            if isinstance(joined_date, datetime):
                date_str = joined_date.strftime("%d/%m/%Y %H:%M")
                days_ago = (datetime.utcnow() - joined_date).days
                if days_ago == 0:
                    date_str += " (Today)"
                elif days_ago == 1:
                    date_str += " (Yesterday)"
                elif days_ago < 30:
                    date_str += f" ({days_ago}d ago)"
            else:
                date_str = "N/A"
            
            # Truncate long names
            display_name = user_name[:25] + "..." if len(str(user_name)) > 25 else user_name
            
            detailed_text += f"<b>#{i:02d}. {' '.join(status_icons)}</b>\n"
            detailed_text += f"├ 👤 <b>User:</b> {display_name}\n"
            detailed_text += f"├ 🆔 <b>ID:</b> <code>{user_id_info}</code>\n"
            detailed_text += f"├ 📅 <b>Joined:</b> {date_str}\n"
            
            # Premium details
            if premium_info:
                expires_at = premium_info.get('expires_at', 'Unknown')
                if isinstance(expires_at, datetime) and not premium_info.get('is_sudo_lifetime'):
                    days_remaining = max(0, (expires_at - datetime.utcnow()).days)
                    detailed_text += f"├ 💎 <b>Premium:</b> {plan_type} ({days_remaining}d left)\n"
                elif premium_info.get('is_sudo_lifetime'):
                    detailed_text += f"├ 👑 <b>Premium:</b> Lifetime Sudo\n"
                else:
                    detailed_text += f"├ 💎 <b>Premium:</b> {plan_type}\n"
            else:
                limit = await db.get_forwarding_limit(user_id_info)
                detailed_text += f"├ 🆓 <b>Plan:</b> Free (Limit: {limit})\n"
            
            # Usage statistics
            monthly_processes = monthly_usage.get('processes', 0)
            daily_processes = daily_usage.get('processes', 0)
            detailed_text += f"├ 📊 <b>Usage:</b> {monthly_processes}M/{daily_processes}D processes\n"
            
            # Ban status
            if ban_status.get('is_banned', False):
                ban_reason = ban_status.get('ban_reason', 'No reason')
                detailed_text += f"├ 🚫 <b>Banned:</b> {ban_reason}\n"
            
            # Referral info
            if user_info.get('referred_by'):
                detailed_text += f"├ 🔗 <b>Referred by:</b> {user_info.get('referred_by')}\n"
            
            referral_code = user_info.get('referral_code', 'None')
            if referral_code and referral_code != 'None':
                referred_count_by_user = referral_stats.get('total_referrals', 0)
                detailed_text += f"├ 🎁 <b>Referral:</b> {referral_code} ({referred_count_by_user} refs)\n"
            
            # Special features
            features = []
            if configs.get('ftm_mode', False):
                features.append("FTM Delta")
            if configs.get('ftm_alpha_mode', False):
                features.append("FTM Alpha")
            if trial_status.get('activated', False):
                features.append("Trial Used")
            
            if features:
                detailed_text += f"└ ⚡ <b>Features:</b> {', '.join(features)}\n"
            else:
                detailed_text += f"└ 📝 <b>Status:</b> Standard User\n"
            
            detailed_text += "\n"
        
        # Create navigation buttons
        keyboard = []
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="users_current_page"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
        
        keyboard.append(nav_buttons)
        
        # Additional action buttons
        action_buttons = [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"users_page_{page}"),
            InlineKeyboardButton("📊 Stats", callback_data="users_show_stats")
        ]
        keyboard.append(action_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Combine header and detailed text
        full_text = header_text + detailed_text
        
        # Add footer
        full_text += f"💡 <b>Navigation:</b> Use arrows to browse pages\n"
        full_text += f"🔧 <b>Commands:</b> /users_detailed [page] • /broadcast\n"
        full_text += f"📊 <b>Updated:</b> {datetime.utcnow().strftime('%H:%M:%S UTC')}"

        await update.message.reply_text(
            text=full_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in PTB users_detailed command for admin {user_id}: {e}", exc_info=True)
        if update.message:
            await update.message.reply_text("❌ An error occurred while fetching detailed users list. Please try again.")

async def handle_users_pagination(update: Update, context: CallbackContext) -> None:
    """Handle pagination callback queries for users_detailed command"""
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer()
    
    user_id = query.from_user.id if query.from_user else None
    if not user_id or not Config.is_sudo_user(user_id):
        await query.edit_message_text("❌ You don't have permission to use this command!")
        return
    
    try:
        # Parse callback data
        if query.data.startswith("users_page_"):
            page = int(query.data.split("_")[-1])
            
            # Get all users from database
            all_users = await db.get_all_users()
            
            if not all_users:
                await query.edit_message_text("📋 No registered users found.")
                return

            # Pagination settings
            users_per_page = 8
            total_users = len(all_users)
            total_pages = max(1, (total_users + users_per_page - 1) // users_per_page)
            page = max(1, min(page, total_pages))  # Clamp page to valid range
            
            start_idx = (page - 1) * users_per_page
            end_idx = min(start_idx + users_per_page, total_users)
            
            # Sort users by join date (newest first)
            sorted_users = sorted(all_users, key=lambda x: x.get('joined_date', datetime.min), reverse=True)
            page_users = sorted_users[start_idx:end_idx]

            # Calculate comprehensive statistics (optimized - done once)
            premium_count = 0
            free_count = 0
            banned_count = 0
            referred_count = 0
            trial_users = 0
            active_today = 0
            active_this_week = 0
            active_this_month = 0
            
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Optimize: batch fetch premium info for page users only for performance
            page_user_ids = [user_info.get('id') for user_info in page_users]
            
            # Gather comprehensive stats from all users (needed for header)
            for user_info in all_users:
                joined_date = user_info.get('joined_date', today)
                ban_status = user_info.get('ban_status', {})
                
                if ban_status.get('is_banned', False):
                    banned_count += 1
                    
                if user_info.get('referred_by'):
                    referred_count += 1
                
                # Activity checks based on join date (simplified for performance)
                if isinstance(joined_date, datetime):
                    if joined_date >= today:
                        active_today += 1
                    if joined_date >= week_ago:
                        active_this_week += 1
                    if joined_date >= month_ago:
                        active_this_month += 1

            # Count premium users (optimized query)
            premium_count = len([u for u in all_users if await db.is_premium_user(u.get('id', 0))])
            free_count = total_users - premium_count

            # Build comprehensive header
            header_text = (
                f"📊 <b>COMPREHENSIVE USER ANALYSIS</b>\n"
                f"═══════════════════════════════════\n\n"
                f"📈 <b>OVERVIEW STATISTICS:</b>\n"
                f"👥 <b>Total Users:</b> {total_users:,}\n"
                f"💎 <b>Premium Users:</b> {premium_count} ({premium_count/total_users*100:.1f}%)\n"
                f"🆓 <b>Free Users:</b> {free_count} ({free_count/total_users*100:.1f}%)\n"
                f"🚫 <b>Banned Users:</b> {banned_count} ({banned_count/total_users*100:.1f}%)\n"
                f"🔗 <b>Referred Users:</b> {referred_count} ({referred_count/total_users*100:.1f}%)\n\n"
                f"📅 <b>ACTIVITY BREAKDOWN:</b>\n"
                f"🆕 <b>Joined Today:</b> {active_today}\n"
                f"📊 <b>Joined This Week:</b> {active_this_week}\n"
                f"📈 <b>Joined This Month:</b> {active_this_month}\n\n"
                f"📄 <b>PAGE {page} of {total_pages}</b> (Users {start_idx + 1}-{end_idx})\n"
                f"═══════════════════════════════════\n\n"
            )
            
            # Build detailed user information (optimized for page users only)
            detailed_text = ""
            for i, user_info in enumerate(page_users, start=start_idx + 1):
                user_id_info = user_info.get('id', 'Unknown')
                user_name = user_info.get('name', 'Unknown')
                joined_date = user_info.get('joined_date', 'Unknown')
                
                # Get user data (only for page users for performance)
                premium_info = await db.get_premium_user_details(user_id_info)
                ban_status = user_info.get('ban_status', {})
                monthly_usage = await db.get_monthly_usage(user_id_info)
                
                # Format user header
                status_icons = []
                plan_type = "FREE"
                if premium_info:
                    plan_type = premium_info.get('plan_type', 'unknown').upper()
                    if premium_info.get('is_sudo_lifetime'):
                        status_icons.append("👑")
                    else:
                        status_icons.append("💎")
                    status_icons.append(f"[{plan_type}]")
                else:
                    status_icons.append("🆓")
                    
                if ban_status.get('is_banned', False):
                    status_icons.append("🚫")
                    
                if user_info.get('referred_by'):
                    status_icons.append("🔗")
                
                # Format join date
                if isinstance(joined_date, datetime):
                    date_str = joined_date.strftime("%d/%m/%Y %H:%M")
                    days_ago = (datetime.utcnow() - joined_date).days
                    if days_ago == 0:
                        date_str += " (Today)"
                    elif days_ago == 1:
                        date_str += " (Yesterday)"
                    elif days_ago < 30:
                        date_str += f" ({days_ago}d ago)"
                else:
                    date_str = "N/A"
                
                # Truncate long names
                display_name = user_name[:25] + "..." if len(str(user_name)) > 25 else user_name
                
                detailed_text += f"<b>#{i:02d}. {' '.join(status_icons)}</b>\n"
                detailed_text += f"├ 👤 <b>User:</b> {display_name}\n"
                detailed_text += f"├ 🆔 <b>ID:</b> <code>{user_id_info}</code>\n"
                detailed_text += f"├ 📅 <b>Joined:</b> {date_str}\n"
                
                # Premium details
                if premium_info:
                    expires_at = premium_info.get('expires_at', 'Unknown')
                    if isinstance(expires_at, datetime) and not premium_info.get('is_sudo_lifetime'):
                        days_remaining = max(0, (expires_at - datetime.utcnow()).days)
                        detailed_text += f"├ 💎 <b>Premium:</b> {plan_type} ({days_remaining}d left)\n"
                    elif premium_info.get('is_sudo_lifetime'):
                        detailed_text += f"├ 👑 <b>Premium:</b> Lifetime Sudo\n"
                    else:
                        detailed_text += f"├ 💎 <b>Premium:</b> {plan_type}\n"
                else:
                    detailed_text += f"├ 🆓 <b>Plan:</b> Free\n"
                
                # Usage statistics
                monthly_processes = monthly_usage.get('processes', 0)
                detailed_text += f"├ 📊 <b>Usage:</b> {monthly_processes} processes this month\n"
                
                # Ban status
                if ban_status.get('is_banned', False):
                    ban_reason = ban_status.get('ban_reason', 'No reason')
                    detailed_text += f"├ 🚫 <b>Banned:</b> {ban_reason}\n"
                
                # Referral info
                if user_info.get('referred_by'):
                    detailed_text += f"├ 🔗 <b>Referred by:</b> {user_info.get('referred_by')}\n"
                
                referral_code = user_info.get('referral_code', 'None')
                if referral_code and referral_code != 'None':
                    detailed_text += f"├ 🎁 <b>Referral Code:</b> {referral_code}\n"
                
                detailed_text += f"└ 📝 <b>Status:</b> Active User\n\n"
            
            # Create navigation buttons
            keyboard = []
            nav_buttons = []
            
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
            
            nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="users_current_page"))
            
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
            
            keyboard.append(nav_buttons)
            
            # Additional action buttons
            action_buttons = [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"users_page_{page}"),
            ]
            keyboard.append(action_buttons)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Combine header and detailed text
            full_text = header_text + detailed_text
            
            # Add footer
            full_text += f"💡 <b>Navigation:</b> Use arrows to browse pages\n"
            full_text += f"🔧 <b>Commands:</b> /users_detailed [page] • /broadcast\n"
            full_text += f"📊 <b>Updated:</b> {datetime.utcnow().strftime('%H:%M:%S UTC')}"

            await query.edit_message_text(
                text=full_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        elif query.data == "users_current_page":
            await query.answer("📄 Current page displayed")
            
    except Exception as e:
        logger.error(f"Error in users pagination handler: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ An error occurred while updating the page. Please try again.")
        except:
            await query.answer("❌ An error occurred while updating the page.")

async def handle_users_actions(update: Update, context: CallbackContext) -> None:
    """Handle action callback queries for users command (revenue, leaderboard, analytics)"""
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer()
    
    user_id = query.from_user.id if query.from_user else None
    if not user_id or not Config.is_sudo_user(user_id):
        await query.edit_message_text("❌ You don't have permission to use this command!")
        return
    
    try:
        if query.data == "users_revenue":
            await query.answer("💰 Showing revenue analytics...")
            # Revenue view would be implemented here
            
        elif query.data == "users_leaderboard":
            await query.answer("🏆 Showing referral leaderboard...")
            # Leaderboard view would be implemented here
            
        elif query.data == "users_analytics":
            await query.answer("📈 Showing detailed analytics...")
            # Analytics view would be implemented here
            
    except Exception as e:
        logger.error(f"Error in users actions handler: {e}", exc_info=True)
        await query.answer("❌ An error occurred while processing the action.")

async def resetall_command(update: Update, context: CallbackContext) -> None:
    """Handle /resetall command - owner only"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    print(f"PTB DEBUG: /resetall command triggered by user {user_id}")
    logger.info(f"PTB Reset all command triggered by admin {user_id}")
    
    # Check if user is the owner
    if user_id != Config.OWNER_ID:
        await update.message.reply_text("❌ You don't have permission to use this command!")
        return
    
    try:
        # Confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton('✅ Yes, Reset All Users', callback_data='confirm_resetall'),
                InlineKeyboardButton('❌ Cancel', callback_data='cancel_resetall')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get total user count
        users_count, _ = await db.total_users_bots_count()
        
        await update.message.reply_text(
            text="<b>🚨 ADMIN RESET ALL CONFIRMATION</b>\n\n"
                 "<b>⚠️ DANGER ZONE ⚠️</b>\n\n"
                 f"<b>This will reset ALL {users_count} users' data including:</b>\n"
                 "• All bot configurations\n"
                 "• All saved channels\n"
                 "• All custom settings\n"
                 "• All captions and buttons\n"
                 "• All filter preferences\n"
                 "• All database connections\n\n"
                 "<b>❗ THIS ACTION CANNOT BE UNDONE!</b>\n"
                 "<b>❗ ALL USER DATA WILL BE PERMANENTLY LOST!</b>\n\n"
                 "<b>Are you absolutely sure?</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in PTB resetall command for admin {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def broadcast_command(update: Update, context: CallbackContext) -> None:
    """Handle /broadcast command - PTB implementation for sudo users only"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    print(f"PTB DEBUG: /broadcast command triggered by user {user_id}")
    logger.info(f"PTB Broadcast command from user {user_id}")
    
    # Check if user is sudo (owner or admin)
    if not Config.is_sudo_user(user_id):
        if update.message:
            await update.message.reply_text("❌ You don't have permission to use this command!")
        return
    
    # Check if it's a reply to a message
    if not update.message.reply_to_message:
        if update.message:
            await update.message.reply_text(
                "📢 <b>Broadcast Usage:</b>\n\n"
                "Reply to the message you want to broadcast to all users with /broadcast\n\n"
                "<b>Example:</b>\n"
                "1. Send or forward the message you want to broadcast\n"
                "2. Reply to it with <code>/broadcast</code>\n"
                "3. The message will be sent to all registered users\n\n"
                "<b>Note:</b> Only admins and owners can use this command.",
                parse_mode=ParseMode.HTML
            )
        return
    
    try:
        # Get all users from database
        all_users = await db.get_all_users()
        
        if not all_users:
            if update.message:
                await update.message.reply_text("📋 No registered users found to broadcast to.")
            return
        
        broadcast_msg = update.message.reply_to_message
        total_users, _ = await db.total_users_bots_count()
        
        # Determine message type for display
        msg_type = "Unknown"
        if broadcast_msg.text:
            msg_type = "Text"
        elif broadcast_msg.photo:
            msg_type = "Photo"
        elif broadcast_msg.video:
            msg_type = "Video"
        elif broadcast_msg.document:
            msg_type = "Document"
        elif broadcast_msg.audio:
            msg_type = "Audio"
        elif broadcast_msg.voice:
            msg_type = "Voice"
        elif broadcast_msg.animation:
            msg_type = "Animation"
        elif broadcast_msg.sticker:
            msg_type = "Sticker"
        
        # Initial status message
        status_msg = await update.message.reply_text(
            f"📢 <b>Broadcasting Message...</b>\n\n"
            f"💬 <b>Message Type:</b> {msg_type}\n"
            f"👥 <b>Total Recipients:</b> {total_users:,}\n"
            f"⏱️ <b>Status:</b> Starting...\n\n"
            f"📊 <b>Progress:</b> 0 / {total_users}",
            parse_mode=ParseMode.HTML
        )
        
        start_time = time.time()
        done = 0
        success = 0
        blocked = 0
        deleted = 0
        failed = 0
        
        # Create a bot instance for sending messages
        bot = context.bot
        
        # Process users in batches
        for user_info in all_users:
            user_chat_id = int(user_info['id'])
            
            result, reason = await broadcast_single_message(
                bot, user_chat_id, broadcast_msg
            )
            
            if result:
                success += 1
                # Add delay to avoid rate limiting
                await asyncio.sleep(0.1)
            else:
                if reason == "Blocked":
                    blocked += 1
                elif reason == "Deleted":
                    deleted += 1
                    # Remove deleted user from database
                    await db.delete_user(user_chat_id)
                    logger.info(f"Removed deleted user {user_chat_id} from database")
                else:
                    failed += 1
            
            done += 1
            
            # Update progress every 20 users
            if done % 20 == 0:
                elapsed_time = time.time() - start_time
                estimated_total = (elapsed_time / done) * total_users if done > 0 else 0
                remaining_time = max(0, estimated_total - elapsed_time)
                
                progress_text = (
                    f"📢 <b>Broadcasting in Progress...</b>\n\n"
                    f"👥 <b>Total Recipients:</b> {total_users:,}\n"
                    f"✅ <b>Completed:</b> {done} / {total_users} ({done/total_users*100:.1f}%)\n"
                    f"🎯 <b>Successful:</b> {success}\n"
                    f"🚫 <b>Blocked:</b> {blocked}\n"
                    f"❌ <b>Deleted:</b> {deleted}\n"
                    f"⚠️ <b>Failed:</b> {failed}\n\n"
                    f"⏱️ <b>Elapsed:</b> {int(elapsed_time//60)}m {int(elapsed_time%60)}s\n"
                    f"⏳ <b>Estimated Remaining:</b> {int(remaining_time//60)}m {int(remaining_time%60)}s"
                )
                
                try:
                    await status_msg.edit_text(progress_text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.warning(f"Could not update progress message: {e}")
        
        # Final summary
        total_time = time.time() - start_time
        time_taken = timedelta(seconds=int(total_time))
        
        # Calculate success rate
        success_rate = (success / total_users * 100) if total_users > 0 else 0
        
        final_text = (
            f"📢 <b>Broadcast Completed!</b>\n\n"
            f"⏱️ <b>Completed in:</b> {time_taken}\n"
            f"👥 <b>Total Recipients:</b> {total_users:,}\n\n"
            f"📊 <b>Results Summary:</b>\n"
            f"✅ <b>Successful:</b> {success} ({success_rate:.1f}%)\n"
            f"🚫 <b>Blocked:</b> {blocked}\n"
            f"❌ <b>Deleted:</b> {deleted}\n"
            f"⚠️ <b>Failed:</b> {failed}\n\n"
            f"📈 <b>Delivery Rate:</b> {'🟢 Excellent' if success_rate >= 90 else '🟡 Good' if success_rate >= 75 else '🔴 Needs Attention'}\n\n"
            f"💡 <b>Tip:</b> Deleted accounts have been automatically removed from the database."
        )
        
        try:
            await status_msg.edit_text(final_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Could not update final broadcast message: {e}")
            if update.message:
                await update.message.reply_text(final_text, parse_mode=ParseMode.HTML)
        
        logger.info(f"Broadcast completed: {success}/{total_users} successful deliveries")
        
    except Exception as e:
        logger.error(f"Error in PTB broadcast command: {e}", exc_info=True)
        if update.message:
            await update.message.reply_text(
                "❌ An error occurred during the broadcast. Please check logs for details."
            )

async def broadcast_single_message(bot: Bot, user_id: int, message) -> tuple[bool, str]:
    """Send a single broadcast message using PTB"""
    try:
        # Handle different message types
        if message.text:
            await bot.send_message(
                chat_id=user_id,
                text=message.text,
                parse_mode=ParseMode.HTML if message.entities else None
            )
        elif message.photo:
            await bot.send_photo(
                chat_id=user_id,
                photo=message.photo[-1].file_id,
                caption=message.caption or None,
                parse_mode=ParseMode.HTML if message.caption else None
            )
        elif message.video:
            await bot.send_video(
                chat_id=user_id,
                video=message.video.file_id,
                caption=message.caption or None,
                parse_mode=ParseMode.HTML if message.caption else None
            )
        elif message.document:
            await bot.send_document(
                chat_id=user_id,
                document=message.document.file_id,
                caption=message.caption or None,
                parse_mode=ParseMode.HTML if message.caption else None
            )
        elif message.audio:
            await bot.send_audio(
                chat_id=user_id,
                audio=message.audio.file_id,
                caption=message.caption or None,
                parse_mode=ParseMode.HTML if message.caption else None
            )
        elif message.voice:
            await bot.send_voice(
                chat_id=user_id,
                voice=message.voice.file_id,
                caption=message.caption or None,
                parse_mode=ParseMode.HTML if message.caption else None
            )
        elif message.animation:
            await bot.send_animation(
                chat_id=user_id,
                animation=message.animation.file_id,
                caption=message.caption or None,
                parse_mode=ParseMode.HTML if message.caption else None
            )
        elif message.sticker:
            await bot.send_sticker(
                chat_id=user_id,
                sticker=message.sticker.file_id
            )
        else:
            # Try to forward the message as fallback
            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id
            )
        
        return True, "Success"
        
    except Forbidden:
        # User blocked the bot
        logger.info(f"User {user_id} has blocked the bot")
        return False, "Blocked"
    except BadRequest as e:
        if "chat not found" in str(e).lower() or "user not found" in str(e).lower():
            # User account deleted
            logger.info(f"User {user_id} account deleted")
            return False, "Deleted"
        else:
            logger.warning(f"Bad request for user {user_id}: {e}")
            return False, "Error"
    except TelegramError as e:
        if "flood" in str(e).lower():
            # Rate limit hit, wait and retry
            wait_time = 30  # Default wait time
            logger.warning(f"Rate limit hit, waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
            return await broadcast_single_message(bot, user_id, message)
        else:
            logger.warning(f"Telegram error for user {user_id}: {e}")
            return False, "Error"
    except Exception as e:
        logger.error(f"Unexpected error broadcasting to user {user_id}: {e}")
        return False, "Error"

def setup_ptb_application() -> Application:
    """Create and configure the python-telegram-bot Application"""
    if not Config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required for PTB application")
    
    # Configure to only handle messages, not callback queries (let Pyrogram handle those)
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("users_detailed", users_detailed_command))
    application.add_handler(CommandHandler("resetall", resetall_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Add callback query handlers for pagination and actions
    application.add_handler(CallbackQueryHandler(handle_users_pagination, pattern="^users_page_"))
    application.add_handler(CallbackQueryHandler(handle_users_pagination, pattern="^users_current_page"))
    application.add_handler(CallbackQueryHandler(handle_users_actions, pattern="^users_(revenue|leaderboard|analytics)"))
    
    return application

if __name__ == "__main__":
    # For testing
    app = setup_ptb_application()
    app.run_polling()