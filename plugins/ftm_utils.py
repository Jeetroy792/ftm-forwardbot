import re
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def create_source_link(chat_id, message_id):
    """Create a source message link"""
    if str(chat_id).startswith('-100'):
        # Channel/Supergroup
        channel_id = str(chat_id)[4:]  # Remove -100 prefix
        return f"https://t.me/c/{channel_id}/{message_id}"
    else:
        # Private chat or bot
        return f"https://t.me/{chat_id}/{message_id}"

def create_target_link(chat_id, message_id):
    """Create a target message link"""
    if str(chat_id).startswith('-100'):
        # Channel/Supergroup
        channel_id = str(chat_id)[4:]  # Remove -100 prefix
        return f"https://t.me/c/{channel_id}/{message_id}"
    else:
        # Private chat or bot
        return f"https://t.me/{chat_id}/{message_id}"

def add_ftm_caption(original_caption, source_link):
    """Add FTM mode information to caption with proper encoding handling"""
    ftm_info = f"\n\n🔥 <b>FTM MODE</b> 🔥\n📤 <b>Source:</b> <a href='{source_link}'>Original Message</a>"
    
    if original_caption:
        # Import here to avoid circular imports
        from plugins.regix import safe_decode_caption
        # Ensure caption is properly decoded before concatenation
        safe_caption = safe_decode_caption(original_caption)
        return safe_caption + ftm_info
    else:
        return ftm_info.strip()

def create_ftm_button(source_link):
    """Create FTM mode button with source link"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Source Link", url=source_link)]
    ])

def combine_buttons(ftm_button, existing_buttons=None):
    """Combine FTM button with existing buttons"""
    if not existing_buttons:
        return ftm_button

    # If existing buttons exist, add FTM button at the top
    ftm_row = ftm_button.inline_keyboard[0]
    new_keyboard = [ftm_row] + existing_buttons.inline_keyboard
    return InlineKeyboardMarkup(new_keyboard)