import os
import sys 
import math
import time
import asyncio 
import logging
import html
from .utils import STS
from database import db
from utils.notifications import NotificationManager 
from .test import CLIENT , start_clone_bot, get_configs
from config import Config, temp
from translation import Translation
from pyrogram import Client, filters 
#from pyropatch.utils import unpack_new_file_id
from pyrogram.errors import FloodWait, MessageNotModified, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from .ftm_utils import create_source_link, create_target_link, add_ftm_caption, create_ftm_button, combine_buttons

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Translation.TEXT

def safe_decode_caption(caption_data):
    """
    Safely decode caption data that might be in various encodings including UTF-16-LE.
    
    Args:
        caption_data: The caption data from Pyrogram (could be string, bytes, or None)
        
    Returns:
        str: Properly decoded UTF-8 string, or empty string if decoding fails
    """
    if not caption_data:
        return ""
    
    # If it's already a string, ensure it's clean UTF-8
    if isinstance(caption_data, str):
        try:
            # Encode and decode to ensure clean UTF-8
            return caption_data.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception:
            return ""
    
    # If it's bytes, try multiple encoding methods
    if isinstance(caption_data, bytes):
        # List of encodings to try, in order of preference
        encodings_to_try = [
            'utf-8',
            'utf-16-le',  # Handle the specific UTF-16-LE encoding issue
            'utf-16-be',
            'utf-16',
            'latin-1',
            'cp1252'
        ]
        
        for encoding in encodings_to_try:
            try:
                decoded = caption_data.decode(encoding, errors='strict')
                # Additional validation: ensure the decoded string is reasonable
                if decoded and len(decoded) > 0:
                    # Clean up any potential null bytes or control characters
                    cleaned = decoded.replace('\x00', '').strip()
                    if cleaned:
                        return cleaned
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # If all encodings fail, try with error handling
        try:
            return caption_data.decode('utf-8', errors='replace').replace('\ufffd', '').strip()
        except Exception:
            return ""
    
    # Fallback for any other type
    try:
        return str(caption_data).encode('utf-8', errors='ignore').decode('utf-8')
    except Exception:
        return ""

@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    user = message.from_user.id
    temp.CANCEL[user] = False
    frwd_id = message.data.split("_")[2]
    if temp.lock.get(user) and str(temp.lock.get(user))=="True":
      return await message.answer("please wait until previous task complete", show_alert=True)
    sts = STS(frwd_id)
    if not sts.verify():
      await message.answer("your are clicking on my old button", show_alert=True)
      return await message.message.delete()
    i = sts.get(full=True)
    if i.TO in temp.IS_FRWD_CHAT:
      return await message.answer("In Target chat a task is progressing. please wait until task complete", show_alert=True)
    m = await msg_edit(message.message, "<code>verifying your data's, please wait.</code>")
    _bot, caption, forward_tag, data, protect, button = await sts.get_data(user)
    if not _bot:
      return await msg_edit(m, "<code>You didn't added any bot. Please add a bot using /settings !</code>", wait=True)
    
    # Check if user is sudo (owner/admin) and ensure they have premium access
    if Config.is_sudo_user(user):
        if not await db.is_premium_user(user):
            # Automatically grant premium to sudo users (expires in 10 years)
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(days=3650)
            await db.add_premium_user(user, plan_type="sudo_unlimited", expires_at=expires_at)
            print(f"Auto-granted premium to sudo user: {user}")
    else:
        # Check usage limits for non-sudo users
        can_process, reason = await db.can_user_process(user)
        if not can_process:
            if reason == "monthly_limit_reached":
                # Initialize notification manager and notify limit exhausted
                notify = NotificationManager(bot)
                await notify.notify_limit_exhausted(user, 1)
                
                limit_msg = """<b>🚫 Monthly Limit Reached!</b>

<b>Free users are limited to 1 process per month.</b>

<b>💎 Upgrade to Premium for unlimited access!</b>
• <b>Price:</b> ₹200/month
• <b>Payment:</b> 8504021912@ptsbi
• <b>Benefits:</b> Unlimited forwarding

<b>How to upgrade:</b>
1. Send ₹200 to <code>8504021912@ptsbi</code>
2. Take screenshot of payment
3. Send screenshot with <code>/verify</code>
4. Wait for admin approval

<b>Your current usage:</b> 1/1 processes used this month
<b>Next reset:</b> 1st of next month"""
                return await msg_edit(m, limit_msg, wait=True)
    
    # Initialize notification manager and notify process start
    notify = NotificationManager(bot)
    await notify.notify_process_start(user, "Forward", sts.get('FROM'), sts.get('TO'))
    
    # Add to queue for crash recovery
    queue_id = await db.add_queue_item(user, {
        'from_chat': sts.get('FROM'),
        'to_chat': sts.get('TO'),
        'total': sts.get('total'),
        'skip': sts.get('skip'),
        'bot_details': _bot
    })
    try:
      client = await start_clone_bot(CLIENT.client(_bot))
    except Exception as e:
      error_msg = f"**Error starting bot:** `{str(e)}`"
      # Send error notification for all users (not just admin)
      try:
          notify = NotificationManager(bot)
          await notify.notify_error(user, "Bot Start Failed", str(e))
      except Exception as notify_err:
          print(f"Failed to send error notification: {notify_err}")
      return await m.edit(error_msg)
    # Status will be updated by validation steps below
    try:
       # Validate channel ID format and test access
       from_chat = sts.get("FROM")
       if isinstance(from_chat, str) and from_chat.lstrip('-').isdigit():
           from_chat = int(from_chat)
       await client.get_messages(from_chat, sts.get("limit"))
    except Exception as e:
       error_msg = f"**Source chat may be a private channel / group. Use userbot (user must be member over there) or if Make Your [Bot](t.me/{_bot['username']}) an admin over there**"
       # Send error notification for all users
       try:
           notify = NotificationManager(bot)
           await notify.notify_error(user, "Source Chat Access Failed", f"Cannot access source chat: {str(e)}")
       except Exception as notify_err:
           print(f"Failed to send error notification: {notify_err}")
       await msg_edit(m, error_msg, retry_btn(frwd_id), True)
       return await stop(client, user)
    try:
       # Validate target channel ID format
       to_chat = i.TO
       if isinstance(to_chat, str) and to_chat.lstrip('-').isdigit():
           to_chat = int(to_chat)
       k = await client.send_message(to_chat, "Testing")
       await k.delete()
    except Exception as e:
       error_msg = f"**Please Make Your [UserBot / Bot](t.me/{_bot['username']}) Admin In Target Channel With Full Permissions**"
       # Send error notification for all users
       try:
           notify = NotificationManager(bot)
           await notify.notify_error(user, "Target Chat Admin Required", f"Bot needs admin permissions in target chat: {str(e)}")
       except Exception as notify_err:
           print(f"Failed to send error notification: {notify_err}")
       await msg_edit(m, error_msg, retry_btn(frwd_id), True)
       return await stop(client, user)
    temp.forwardings += 1
    await db.add_frwd(user)
    
    # Increment usage count for non-premium users (premium users have unlimited)
    if not Config.is_sudo_user(user) and not await db.is_premium_user(user):
        await db.increment_usage(user)
    
    await send(client, user, "<b>𝙵𝙾𝚁𝚆𝙰𝚁𝙳𝙸𝙽𝙶 𝚂𝚃𝙰𝚁𝚃𝙴𝙳 𝙱𝚈 <a href=https://t.me/ftmdeveloper>𝙵𝚃𝙼 𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁</a></b>")
    sts.add(time=True)
    sleep = 1.5  # Optimized sleep time for both bots and userbots
    await msg_edit(m, "<code>Processing...</code>") 
    temp.IS_FRWD_CHAT.append(i.TO)
    temp.lock[user] = locked = True
    if locked:
        try:
          MSG = []
          pling=0
          await edit(m, 'Progressing', 10, sts)
          print(f"Starting Forwarding Process... From :{sts.get('FROM')} To: {sts.get('TO')} Totel: {sts.get('limit')} stats : {sts.get('skip')})")
          # Use validated channel ID for iteration
          from_chat_validated = sts.get('FROM')
          if isinstance(from_chat_validated, str) and from_chat_validated.lstrip('-').isdigit():
              from_chat_validated = int(from_chat_validated)
          
          async for message in client.iter_messages(
            chat_id=from_chat_validated, 
            limit=int(sts.get('limit')), 
            offset=int(sts.get('skip')) if sts.get('skip') else 0
            ):
                if await is_cancelled(client, user, m, sts):
                   return
                # Update progress more frequently (every 10 messages for better responsiveness)
                if pling %10 == 0: 
                   await edit(m, 'Progressing', 10, sts)
                pling += 1
                sts.add('fetched')
                if message == "DUPLICATE":
                   sts.add('duplicate')
                   continue 
                elif message == "FILTERED":
                   sts.add('filtered')
                   continue 
                if message.empty or message.service:
                   sts.add('deleted')
                   continue

                # Apply filters
                filter_result = await should_forward_message(message, user)
                print(f"Message {message.id}: Filter result: {filter_result}")
                if message.photo and message.caption:
                    print(f"Message {message.id}: Has photo + caption (image+text)")
                elif message.photo:
                    print(f"Message {message.id}: Has photo only")
                elif message.text:
                    print(f"Message {message.id}: Has text only")

                if not filter_result:
                   print(f"Message {message.id}: FILTERED OUT")
                   sts.add('filtered')
                   continue
                else:
                   print(f"Message {message.id}: PASSED FILTER - will be forwarded")

                # Check for duplicates
                if await is_duplicate_message(message, user):
                   sts.add('duplicate')
                   continue
                
                # Check if message has media (photo, video, document, audio, voice, animation, sticker)
                has_media = bool(message.photo or message.video or message.document or 
                               message.audio or message.voice or message.animation or 
                               message.sticker)
                
                # Force media messages to be copied individually (without tags)
                # Only use batch forwarding for text-only messages when forward_tag is enabled
                if forward_tag and not has_media:
                   MSG.append(message.id)
                   notcompleted = len(MSG)
                   completed = sts.get('total') - sts.get('fetched')
                   if ( notcompleted >= 100 
                        or completed <= 100): 
                      # Get FTM mode status - only allow for Pro plan users
                      configs = await get_configs(user)
                      user_can_use_ftm = await db.can_use_ftm_mode(user)
                      ftm_mode = configs.get('ftm_mode', False) and user_can_use_ftm
                      # Forward returns True/False, count is handled internally
                      await forward(client, MSG, m, sts, protect, ftm_mode, _bot['is_bot'])
                      await asyncio.sleep(1.5)
                      MSG = []
                else:
                   # Handle text messages vs media messages differently
                   if message.text:
                       # For text messages, use the actual text content
                       message_content = message.text
                       print(f"Message {message.id}: Using message.text = '{message_content[:50]}...'")
                   else:
                       # For media messages, only apply custom caption if user has explicitly set one
                       if caption is not None:
                           # User has set a custom caption, apply it
                           message_content = custom_caption(message, caption)
                           print(f"Message {message.id}: Using custom caption = '{message_content[:50] if message_content else None}...'")
                       else:
                           # No custom caption set, use original caption unchanged with safe decoding
                           message_content = safe_decode_caption(message.caption)
                           print(f"Message {message.id}: Using original caption = '{message_content[:50] if message_content else None}...'")
                   
                   # For media messages without text content, we don't need to validate content is not empty
                   # because media can exist without captions
                   
                   # Get FTM mode status - only allow for Pro plan users
                   configs = await get_configs(user)
                   user_can_use_ftm = await db.can_use_ftm_mode(user)
                   ftm_mode = configs.get('ftm_mode', False) and user_can_use_ftm
                   details = {"msg_id": message.id, "media": media(message), "caption": message_content, 'button': button, "protect": protect, "ftm_mode": ftm_mode, "is_bot": _bot['is_bot']}
                   # Call copy - it handles its own counting internally
                   await copy(client, details, m, sts)
                   await asyncio.sleep(sleep) 
        except Exception as e:
            error_msg = f'<b>ERROR:</b>\n<code>{e}</code>'
            # Send error notification for all users (not restricted to admins)
            try:
                notify = NotificationManager(bot)
                await notify.notify_error(user, "Forwarding Process Failed", str(e))
            except Exception as notify_err:
                print(f"Failed to send error notification: {notify_err}")
            
            await msg_edit(m, error_msg, wait=True)
            temp.IS_FRWD_CHAT.remove(sts.TO)
            return await stop(client, user)
        temp.IS_FRWD_CHAT.remove(sts.TO)
        await send(client, user, "<b>🎉 𝙵𝙾𝚁𝚆𝙰𝚁𝙳𝙸𝙽𝙶 𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴𝙳 𝙱𝚈 🥀 <a href=https://t.me/ftmdeveloperz>𝙵𝚃𝙼 𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁</a>🥀</b>")
        await edit(m, 'Completed', "completed", sts, force=True)
        
        # Send completion notification
        stats = {
            'fetched': sts.get('fetched'),
            'forwarded': sts.get('forwarded'), 
            'filtered': sts.get('filtered'),
            'duplicate': sts.get('duplicate'),
            'deleted': sts.get('deleted')
        }
        await notify.notify_process_completed(user, "Forward", sts.get('FROM'), sts.get('TO'), stats)
        
        # Mark queue as completed
        await db.update_queue_status(user, 'completed')
        await stop(client, user)

async def copy(bot, msg, m, sts):
   try:
     if 'button' in msg and msg['button']:
        # Check if FTM mode is enabled
        if msg.get('ftm_mode', False):
           source_link = create_source_link(sts.get('FROM'), msg['msg_id'])
           ftm_button = create_ftm_button(source_link)
           
           # Combine FTM button with existing button
           combined_button = combine_buttons(ftm_button, msg['button'])
           
           # Add FTM info to caption
           caption_with_ftm = add_ftm_caption(msg['caption'], source_link)
           
           sent_msg = await bot.send_message(
               sts.get('TO'), 
               caption_with_ftm, 
               reply_markup=combined_button, 
               protect_content=msg['protect']
           )
           
           # Update with target link if using userbot
           if sent_msg and not msg.get('is_bot', True):
              target_link = create_target_link(sts.get('TO'), sent_msg.id)
              updated_caption = add_ftm_caption(msg['caption'], source_link, target_link)
              try:
                 await sent_msg.edit_text(updated_caption, reply_markup=combined_button)
              except Exception as edit_e:
                 print(f"Failed to edit message with target link: {edit_e}")
        else:
           await bot.send_message(sts.get('TO'), msg['caption'], reply_markup=msg['button'], protect_content=msg['protect'])
     else:
        media_file_id = msg['media']
        if media_file_id:
           # Get original caption and user's custom caption setting
           original_caption = msg['caption']
           user_custom_caption = msg.get('custom_caption', None)  # Only modify if explicitly set
           
           # Determine final caption to use
           if user_custom_caption is not None:
               # User has set a custom caption, apply it
               caption = custom_caption(msg, user_custom_caption)
           else:
               # No custom caption set, use original caption unchanged
               caption = original_caption
           
           # Handle potential encoding issues in caption using the robust decoder
           caption = safe_decode_caption(caption)
           
           # Check if FTM mode is enabled
           if msg.get('ftm_mode', False):
              source_link = create_source_link(sts.get('FROM'), msg['msg_id'])
              ftm_button = create_ftm_button(source_link)
              
              # Add FTM info to caption
              caption_with_ftm = add_ftm_caption(caption, source_link)
              
              # Use copy_message with FTM features - works for both bots and userbots
              sent_msg = await bot.copy_message(
                  chat_id=sts.get('TO'),
                  from_chat_id=sts.get('FROM'),
                  message_id=msg['msg_id'],
                  caption=caption_with_ftm,
                  reply_markup=ftm_button,
                  protect_content=msg['protect']
              )
              
              # Update with target link if using userbot (userbots have more capabilities)
              if sent_msg and not msg.get('is_bot', True):
                 target_link = create_target_link(sts.get('TO'), sent_msg.id)
                 updated_caption = add_ftm_caption(caption, source_link)
                 try:
                    await sent_msg.edit_caption(updated_caption, reply_markup=ftm_button)
                 except Exception as edit_e:
                    print(f"Failed to edit caption with target link: {edit_e}")
           else:
              # Normal copy without FTM - compatible with both bots and userbots
              try:
                  await bot.copy_message(
                      chat_id=sts.get('TO'),
                      from_chat_id=sts.get('FROM'),
                      message_id=msg['msg_id'],
                      caption=caption,
                      protect_content=msg['protect']
                  )
                  
              except Exception as copy_error:
                  # Detect if message was forwarded with forward tag instead of copied
                  # This happens when the message couldn't be copied and was forwarded instead
                  try:
                      # Try to forward the message instead (this creates forward tag)
                      await bot.forward_messages(
                          chat_id=sts.get('TO'),
                          from_chat_id=sts.get('FROM'),
                          message_ids=msg['msg_id']
                      )
                      
                      # Log the forwarding issue
                      notify = NotificationManager(bot)
                      await notify.notify_forwarding_issue(
                          user_id=sts.get('user_id', 'unknown'),
                          issue_type="Forward tag detected",
                          details=f"Message {msg['msg_id']} from {sts.get('FROM')} was forwarded instead of copied due to: {str(copy_error)}"
                      )
                  except Exception as forward_error:
                      print(f"Both copy and forward failed. Copy error: {copy_error}, Forward error: {forward_error}")
                      # Increment error counter for failed message
                      sts.add(deleted=True)
                  # Fallback: try using forward_messages (plural) method
                  try:
                      await bot.forward_messages(
                          chat_id=sts.get('TO'),
                          from_chat_id=sts.get('FROM'),
                          message_ids=[msg['msg_id']],
                          protect_content=msg['protect']
                      )
                      print(f"Successfully forwarded message {msg['msg_id']} using forward_messages fallback")
                  except Exception as forward_error:
                      print(f"Forward messages also failed: {forward_error}")
                      # Don't raise error - mark as failed but continue
                      sts.add('deleted')  # Count as failed forward
                      return False  # Return False to indicate failure
        else:
           # Handle potential encoding issues in message text
           text_content = msg['caption']
           if text_content:
              try:
                 text_content = str(text_content).encode('utf-8', errors='ignore').decode('utf-8')
                 # Check if text is empty after cleaning
                 if not text_content or not text_content.strip():
                    print(f"Message {msg.get('msg_id')}: Text content is empty after encoding cleanup")
                    text_content = "📝 Message content unavailable"
              except (UnicodeDecodeError, UnicodeEncodeError) as enc_error:
                 print(f"Encoding error in text: {enc_error}")
                 text_content = "📝 Text encoding error"
           else:
              # If no text content, add a placeholder
              text_content = "📝 Message content unavailable"
           
           # Check if FTM mode is enabled for text messages
           if msg.get('ftm_mode', False):
              source_link = create_source_link(sts.get('FROM'), msg['msg_id'])
              ftm_button = create_ftm_button(source_link)
              
              # Add FTM info to text content
              text_with_ftm = add_ftm_caption(text_content, source_link)
              
              sent_msg = await bot.send_message(
                  sts.get('TO'), 
                  text_with_ftm, 
                  reply_markup=ftm_button,
                  protect_content=msg['protect']
              )
              
              # Update with target link if using userbot
              if sent_msg and not msg.get('is_bot', True):
                 target_link = create_target_link(sts.get('TO'), sent_msg.id)
                 updated_text = add_ftm_caption(text_content, source_link, target_link)
                 try:
                    await sent_msg.edit_text(updated_text, reply_markup=ftm_button)
                 except Exception as edit_e:
                    print(f"Failed to edit text with target link: {edit_e}")
           else:
              # Normal text message - compatible with both bots and userbots
              try:
                  # Double check text content is not empty before sending
                  if text_content and text_content.strip():
                      await bot.send_message(sts.get('TO'), text_content, protect_content=msg['protect'])
                  else:
                      # If text is still empty, try copying the original message
                      await bot.copy_message(
                          chat_id=sts.get('TO'),
                          from_chat_id=sts.get('FROM'),
                          message_id=msg['msg_id'],
                          protect_content=msg['protect']
                      )
              except Exception as send_error:
                  print(f"Send message failed: {send_error}")
                  # Fallback: try copy_message for text (works better for some bots)
                  try:
                      await bot.copy_message(
                          chat_id=sts.get('TO'),
                          from_chat_id=sts.get('FROM'),
                          message_id=msg['msg_id'],
                          protect_content=msg['protect']
                      )
                  except Exception as copy_error:
                      print(f"Copy message fallback also failed: {copy_error}")
                      # Message failed to send - mark as deleted/failed, not successful
                      print(f"Message {msg['msg_id']}: FAILED to forward - marking as deleted")
                      sts.add('deleted')
                      return False  # Return False to indicate failure
     
     # Only count as successful if we reach this point (no exceptions)
     sts.add('total_files')
     return True  # Return True to indicate success
   except FloodWait as e:
     await edit(m, 'Progressing', e.value, sts, force=True)
     await asyncio.sleep(e.value)
     await edit(m, 'Progressing', 10, sts, force=True)
     await copy(bot, msg, m, sts)
   except (UnicodeDecodeError, UnicodeEncodeError) as enc_error:
     print(f"Encoding error during copy: {enc_error}")
     sts.add('deleted')
     return False
   except Exception as e:
     print(f"ERROR copying message {msg.get('msg_id')}: {e}")
     import traceback
     traceback.print_exc()
     sts.add('deleted')
     return False

async def forward(bot, msg, m, sts, protect, ftm_mode=False, is_bot=True):
   try:
     if ftm_mode:
        # For FTM mode, copy messages individually to add buttons/captions
        for msg_id in msg:
           try:
              # Get the original message to process with FTM
              original_msg = await bot.get_messages(sts.get('FROM'), msg_id)
              if original_msg and not original_msg.empty and not original_msg.service:
                 source_link = create_source_link(sts.get('FROM'), msg_id)
                 ftm_button = create_ftm_button(source_link)

                 # Add FTM info to caption with source link
                 caption = original_msg.caption if original_msg.caption else ""
                 caption = add_ftm_caption(caption, source_link)

                 # Send the message first
                 sent_msg = await bot.copy_message(
                    chat_id=sts.get('TO'),
                    from_chat_id=sts.get('FROM'),
                    message_id=msg_id,
                    caption=caption,
                    reply_markup=ftm_button,
                    protect_content=protect
                 )

                 # Only update with target link if using userbot
                 if sent_msg and not is_bot:
                    target_link = create_target_link(sts.get('TO'), sent_msg.id)
                    updated_caption = add_ftm_caption(original_msg.caption if original_msg.caption else "", source_link, target_link)
                    try:
                       await sent_msg.edit_caption(
                          caption=updated_caption,
                          reply_markup=ftm_button
                       )
                    except Exception as edit_e:
                       print(f"Failed to edit caption with target link: {edit_e}")

              await asyncio.sleep(1.5)  # Optimized delay between messages
           except Exception as e:
              print(f"FTM forward individual error: {e}")
     else:
        # Normal forwarding without FTM
        await bot.forward_messages(
              chat_id=sts.get('TO'),
              from_chat_id=sts.get('FROM'), 
              protect_content=protect,
              message_ids=msg)
        
        # Only count successful forwards (one for each message in the batch)
        if isinstance(msg, list):
            for _ in msg:
                sts.add('total_files')
        else:
            sts.add('total_files')

   except FloodWait as e:
     await edit(m, 'Progressing', e.value, sts, force=True)
     await asyncio.sleep(e.value)
     await edit(m, 'Progressing', 10, sts, force=True)
     await forward(bot, msg, m, sts, protect, ftm_mode, is_bot)

PROGRESS = """
📈 Percetage: {0} %

♻️ Feched: {1}

♻️ Fowarded: {2}

♻️ Remaining: {3}

♻️ Stataus: {4}

⏳️ ETA: {5}
"""

# Global variable to track last edit time
last_edit_time = {}

async def msg_edit(msg, text, button=None, wait=None, force=False):
    # Time-based throttling - only edit if at least 3 seconds have passed
    msg_id = getattr(msg, 'id', str(msg))
    current_time = time.time()
    
    if not force and msg_id in last_edit_time:
        time_diff = current_time - last_edit_time[msg_id]
        if time_diff < 3.0:  # Minimum 3 seconds between edits
            return None
    
    try:
        result = await msg.edit(text, reply_markup=button)
        last_edit_time[msg_id] = current_time
        return result
    except MessageNotModified:
        pass 
    except FloodWait as e:
        if wait:
           # Exponential backoff for FloodWait errors
           sleep_time = min(e.value, 60)  # Cap at 60 seconds
           await asyncio.sleep(sleep_time)
           return await msg_edit(msg, text, button, wait, force=True)

# Time tracking for edit function
edit_last_time = {}

async def edit(msg, title, status, sts, force=False):
   i = sts.get(full=True)
   status = 'Forwarding' if status == 10 else f"Sleeping {status} s" if str(status).isnumeric() else status
   percentage = "{:.0f}".format(float(i.fetched)*100/float(i.total))

   now = time.time()
   diff = int(now - i.start)
   speed = sts.divide(i.fetched, diff)
   elapsed_time = round(diff) * 1000
   time_to_completion = round(sts.divide(i.total - i.fetched, int(speed))) * 1000
   estimated_total_time = elapsed_time + time_to_completion  
   progress = "◉{0}{1}".format(
       ''.join(["◉" for j in range(math.floor(int(percentage) / 10))]),
       ''.join(["◎" for j in range(10 - math.floor(int(percentage) / 10))]))
   button =  [[InlineKeyboardButton(title, f'fwrdstatus#{status}#{estimated_total_time}#{percentage}#{i.id}')]]
   estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)
   estimated_total_time = estimated_total_time if estimated_total_time != '' else '0 s'

   # Calculate filtered/deleted count for better display
   filtered_deleted = i.deleted + i.filtered
   
   # Fixed text format with correct field mapping 
   # TEXT template: total, fetched, successfully_fwd, duplicate, deleted/filtered, skipped, status, progress%, eta, progress_bar
   text = TEXT.format(i.total, i.fetched, i.total_files, i.duplicate, filtered_deleted, i.skip, status, percentage, estimated_total_time, progress)
   if status in ["cancelled", "completed"]:
      button.append(
         [InlineKeyboardButton('Support', url='https://t.me/ftmbotzsupportz'),
         InlineKeyboardButton('Updates', url='https://t.me/ftmbotz')]
         )
   else:
      button.append([InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')])
   # Time-based throttling for edit function
   msg_id = getattr(msg, 'id', str(msg))
   current_time = time.time()
   
   if not force and msg_id in edit_last_time:
       time_diff = current_time - edit_last_time[msg_id]
       if time_diff < 2.0:  # Minimum 2 seconds between progress updates
           return
   
   await msg_edit(msg, text, InlineKeyboardMarkup(button), force=force)
   edit_last_time[msg_id] = current_time

async def is_cancelled(client, user, msg, sts):
   if temp.CANCEL.get(user)==True:
      temp.IS_FRWD_CHAT.remove(sts.TO)
      await edit(msg, "Cancelled", "completed", sts, force=True)
      await send(client, user, "<b>❌ Forwarding Process Cancelled</b>")
      # Mark queue as cancelled
      await db.update_queue_status(user, 'cancelled')
      await stop(client, user)
      return True 
   return False 

async def should_forward_message(message, user_id):
    """Check if message should be forwarded based on user filters"""
    try:
        configs = await get_configs(user_id)
        filters = configs.get('filters', {})

        print(f"=== FILTER CHECK for Message {message.id} ===")
        print(f"User configs keys: {list(configs.keys())}")
        print(f"User filters: {filters}")
        print(f"Keywords config: {configs.get('keywords', [])}")
        print(f"Image+text filter: {filters.get('image_text', False)}")
        print(f"Message type: text={bool(message.text)}, photo={bool(message.photo)}, video={bool(message.video)}")
        print(f"Message caption: {bool(message.caption)}")
        
        if message.caption:
            try:
                caption_preview = safe_decode_caption(message.caption)[:50]
                print(f"Caption content: '{caption_preview}...'")
            except:
                print(f"Caption content: [ENCODING ERROR]")

        # Check message type filters
        print(f"Checking message type filters...")
        
        # Check if any filters are actually enabled (not default True values)
        # If no filters are explicitly set to True, allow all messages (backward compatibility)
        any_filter_enabled = any(filters.get(filter_type, False) for filter_type in 
                               ['text', 'photo', 'video', 'document', 'audio', 'voice', 'animation', 'sticker', 'poll', 'image_text'])
        
        if not any_filter_enabled:
            print(f"Message {message.id}: No specific filters enabled - allowing all message types")
            message_allowed = True
        else:
            # At least one filter is enabled, so check individual message type filters
            message_allowed = False
            
            # Check image+text filter first (special case - requires both image AND text/caption)
            if filters.get('image_text', False):
                has_image = bool(message.photo)
                has_text_or_caption = bool(message.caption and message.caption.strip()) or bool(message.text and message.text.strip())
                if has_image and has_text_or_caption:
                    print(f"Message {message.id}: PASSED image+text filter (has both image and text/caption)")
                    message_allowed = True
            
            # Check individual message type filters (using if instead of elif so multiple can match)
            if message.text and filters.get('text', False):
                print(f"Message {message.id}: Text message - filter ENABLED")
                message_allowed = True
            if message.photo and filters.get('photo', False):
                print(f"Message {message.id}: Photo message - filter ENABLED")
                message_allowed = True
            if message.video and filters.get('video', False):
                print(f"Message {message.id}: Video message - filter ENABLED")
                message_allowed = True
            if message.document and filters.get('document', False):
                print(f"Message {message.id}: Document message - filter ENABLED")
                message_allowed = True
            if message.audio and filters.get('audio', False):
                print(f"Message {message.id}: Audio message - filter ENABLED")
                message_allowed = True
            if message.voice and filters.get('voice', False):
                print(f"Message {message.id}: Voice message - filter ENABLED")
                message_allowed = True
            if message.animation and filters.get('animation', False):
                print(f"Message {message.id}: Animation message - filter ENABLED")
                message_allowed = True
            if message.sticker and filters.get('sticker', False):
                print(f"Message {message.id}: Sticker message - filter ENABLED")
                message_allowed = True
            if message.poll and filters.get('poll', False):
                print(f"Message {message.id}: Poll message - filter ENABLED")
                message_allowed = True
                
            if not message_allowed:
                print(f"Message {message.id}: REJECTED - message type not enabled in filters")
                return False

        # Check file size limit
        file_size_limit = configs.get('file_size', 0)
        size_limit_type = configs.get('size_limit')

        print(f"Checking file size limit: {file_size_limit} MB, type: {size_limit_type}")
        if file_size_limit > 0 and message.media:
            media = getattr(message, message.media.value, None)
            if media and hasattr(media, 'file_size'):
                file_size_mb = media.file_size / (1024 * 1024)  # Convert to MB
                print(f"File size: {file_size_mb:.2f} MB")

                if size_limit_type is True:  # More than
                    if file_size_mb <= file_size_limit:
                        print(f"Message {message.id}: REJECTED - file size {file_size_mb:.2f} MB <= {file_size_limit} MB")
                        return False
                elif size_limit_type is False:  # Less than
                    if file_size_mb >= file_size_limit:
                        print(f"Message {message.id}: REJECTED - file size {file_size_mb:.2f} MB >= {file_size_limit} MB")
                        return False

        # Check extension filters
        extensions = configs.get('extension')
        print(f"Extension filters: {extensions}")
        if extensions and message.document:
            file_name = getattr(message.document, 'file_name', '')
            if file_name:
                file_ext = file_name.split('.')[-1].lower()
                print(f"File extension: {file_ext}")
                if file_ext in [ext.lower().strip('.') for ext in extensions]:
                    print(f"Message {message.id}: REJECTED - extension {file_ext} is filtered")
                    return False

        # Check keyword filters
        keywords = configs.get('keywords', [])
        print(f"Keyword filters: {keywords}")
        if keywords and len(keywords) > 0:
            message_text = ""
            if message.text:
                message_text = message.text.lower()
            elif message.caption:
                message_text = message.caption.lower()
            elif message.document and hasattr(message.document, 'file_name'):
                message_text = message.document.file_name.lower()

            print(f"Message text for keyword check: '{message_text[:100]}...'")
            if message_text:
                # If keywords are set, message must contain at least one keyword
                keyword_found = any(keyword.lower().strip() in message_text for keyword in keywords if keyword.strip())
                print(f"Keyword found: {keyword_found}")
                if not keyword_found:
                    print(f"Message {message.id}: REJECTED - no keywords found")
                    return False
            else:
                print(f"Message {message.id}: REJECTED - no text content for keyword matching")
                return False

        print(f"Message {message.id}: PASSED all filters")
        return True
    
    except Exception as e:
        print(f"Error in should_forward_message: {e}")
        import traceback
        traceback.print_exc()
        return True  # Default to allow forwarding if there's an error

async def is_duplicate_message(message, user_id):
    """Check if message is duplicate based on user settings"""
    configs = await get_configs(user_id)

    if not configs.get('duplicate', True):
        return False  # Duplicate checking is disabled

    # Simple duplicate check based on file_id for media messages
    if message.media:
        media = getattr(message, message.media.value, None)
        if media and hasattr(media, 'file_unique_id'):
            # Here you could implement database storage of seen file IDs
            # For now, we'll return False to not block any messages
            # You can enhance this with proper duplicate tracking
            pass

    return False

async def stop(client, user):
   try:
     await client.stop()
   except:
     pass 
   await db.rmve_frwd(user)
   temp.forwardings -= 1
   temp.lock[user] = False 

async def send(bot, user, text):
   try:
      await bot.send_message(user, text=text)
   except:
      pass 

def custom_caption(message, caption):
    if message.caption:
       # Use the robust encoding handler for original caption
       old_caption = safe_decode_caption(message.caption)
       old_caption = html.escape(old_caption) if old_caption else ""

       if caption:
          # Use safe decoding for custom caption as well
          caption = safe_decode_caption(caption)
          new_caption = caption.replace('{caption}', old_caption) if caption else old_caption
       else:
          new_caption = old_caption 
    else:
       if caption:
          # Use safe decoding for custom caption when there's no original caption
          new_caption = safe_decode_caption(caption)
       else:
          new_caption = ""
    return new_caption

def get_size(size):
  units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
  size = float(size)
  i = 0
  while size >= 1024.0 and i < len(units):
     i += 1
     size /= 1024.0
  return "%.2f %s" % (size, units[i]) 

def media(msg):
  if msg.media:
     media = getattr(msg, msg.media.value, None)
     if media:
        return getattr(media, 'file_id', None)
  return None 

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

def retry_btn(id):
    return InlineKeyboardMarkup([[InlineKeyboardButton('♻️ RETRY ♻️', f"start_public_{id}")]])

@Client.on_callback_query(filters.regex(r'^terminate_frwd$'))
async def terminate_frwding(bot, m):
    user_id = m.from_user.id 
    temp.lock[user_id] = False
    temp.CANCEL[user_id] = True 
    await m.answer("Forwarding cancelled !", show_alert=True)

@Client.on_callback_query(filters.regex(r'^fwrdstatus'))
async def status_msg(bot, msg):
    _, status, est_time, percentage, frwd_id = msg.data.split("#")
    sts = STS(frwd_id)
    if not sts.verify():
       fetched, forwarded, remaining = 0
    else:
       fetched, forwarded = sts.get('fetched'), sts.get('total_files')
       remaining = fetched - forwarded 
    est_time = TimeFormatter(milliseconds=est_time)
    est_time = est_time if (est_time != '' or status not in ['completed', 'cancelled']) else '0 s'
    return await msg.answer(PROGRESS.format(percentage, fetched, forwarded, remaining, status, est_time), show_alert=True)

@Client.on_callback_query(filters.regex(r'^close_btn$'))
async def close(bot, update):
    await update.answer()
    await update.message.delete()
