import re, asyncio
import logging
from database import db
from config import temp, Config
from .test import CLIENT , start_clone_bot
from .fsub import send_force_subscribe_message
from translation import Translation
from utils.notifications import NotificationManager
from pyrogram import Client, filters 
from pyrogram.file_id import FileId
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

CLIENT = CLIENT()

COMPLETED_BTN = InlineKeyboardMarkup(
   [
      [InlineKeyboardButton('⚡ Support', url='https://t.me/ftmbotzsupportz')],
      [InlineKeyboardButton('📢 Updates', url='https://t.me/ftmbotzofficial')]
   ]
)

CANCEL_BTN = InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')]])

@Client.on_message(filters.private & filters.command(['unequify']))
async def unequify(client, message):
   user_id = message.from_user.id
   user_name = message.from_user.first_name
   logger.info(f"Unequify command from user {user_id} ({user_name})")
   
   # Check force subscribe for non-sudo users
   force_sub_msg = await send_force_subscribe_message(message, client)
   if force_sub_msg:
       return
   
   # Send start notification to log channel
   try:
       notify = NotificationManager(client)
       await notify.notify_user_action(user_id, "Started Unequify Process", "Duplicate message removal")
   except Exception as notify_err:
       logger.error(f"Failed to send unequify start notification: {notify_err}")
   
   temp.CANCEL[user_id] = False
   if temp.lock.get(user_id) and str(temp.lock.get(user_id))=="True":
      return await message.reply(
          "<b>⏳ Process Already Running</b>\n\n"
          "<b>❌ You already have an active unequify process running.</b>\n\n"
          "<b>💡 Please wait until the current process is completed before starting a new one.</b>"
      )
   _bot = await db.get_bot(user_id)
   if not _bot or _bot['is_bot']:
      return await message.reply(
          "<b>🤖 Userbot Required</b>\n\n"
          "<b>❌ The unequify process requires a userbot account, not a regular bot.</b>\n\n"
          "<b>📝 How to fix this:</b>\n"
          "• Use /settings command to add your userbot\n"
          "• Make sure it's a real Telegram user account\n"
          "• Ensure the userbot has admin permissions in the target chat\n\n"
          "<b>💡 Need help? Use /contact to reach admin support.</b>"
      )
   target = await client.ask(user_id, text="**Forward the last message from target chat or send last message link.**\n/cancel - `cancel this process`")
   if target.text.startswith("/"):
      return await message.reply(
          "<b>❌ Process Cancelled</b>\n\n"
          "<b>The unequify process has been cancelled by your request.</b>\n\n"
          "<b>💡 You can restart the process anytime using /unequify command.</b>"
      )
   elif target.text:
      regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
      match = regex.match(target.text.replace("?single", ""))
      if not match:
         return await message.reply(
           "<b>🔗 Invalid Link Format</b>\n\n"
           "<b>❌ The link you provided is not a valid Telegram message link.</b>\n\n"
           "<b>✅ Valid formats:</b>\n"
           "• https://t.me/channelname/123\n"
           "• https://t.me/c/1234567/123\n"
           "• @channelname/123\n\n"
           "<b>💡 Make sure to copy the complete message link from Telegram.</b>"
       )
      chat_id = match.group(4)
      last_msg_id = int(match.group(5))
      if chat_id.isnumeric():
         chat_id  = int(("-100" + chat_id))
   elif target.forward_from_chat and target.forward_from_chat.type in ['channel', 'supergroup']:
        last_msg_id = target.forward_from_message_id
        chat_id = target.forward_from_chat.username or target.forward_from_chat.id
   else:
        return await message.reply_text(
            "<b>📨 Invalid Message</b>\n\n"
            "<b>❌ Please provide either:</b>\n"
            "• Forward the last message from target chat, OR\n"
            "• Send the last message link from target chat\n\n"
            "<b>💡 The message must be from a channel or supergroup.</b>"
        )
   confirm = await client.ask(user_id, text="**send /yes to start the process and /no to cancel this process**")
   if confirm.text.lower() == '/no':
      return await confirm.reply(
          "<b>❌ Process Cancelled</b>\n\n"
          "<b>The unequify process has been cancelled by your request.</b>\n\n"
          "<b>💡 You can restart the process anytime using /unequify command.</b>"
      )
   sts = await confirm.reply("`processing..`")
   try:
      bot = await start_clone_bot(CLIENT.client(_bot))
   except Exception as e:
      error_msg = f"**Error starting bot:** `{str(e)}`"
      return await sts.edit(error_msg)
   try:
       k = await bot.send_message(chat_id, text="testing")
       await k.delete()
   except:
       await sts.edit(
           f"<b>🔐 Admin Access Required</b>\n\n"
           f"<b>❌ Your userbot @{_bot['username']} needs admin permissions in the target chat.</b>\n\n"
           f"<b>📋 Required permissions:</b>\n"
           f"• Delete messages\n"
           f"• Read message history\n"
           f"• Send messages\n\n"
           f"<b>🔧 Please make your [userbot](t.me/{_bot['username']}) admin with full permissions and try again.</b>"
       )
       return await bot.stop()
   MESSAGES = []
   DUPLICATE = []
   total=deleted=0
   temp.lock[user_id] = True
   try:
     await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
     async for message in bot.search_messages(chat_id=chat_id, filter="document"):
        if temp.CANCEL.get(user_id) == True:
           await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴄᴀɴᴄᴇʟʟᴇᴅ"), reply_markup=COMPLETED_BTN)
           return await bot.stop()
        file = message.document
        if file is None:
           continue
        try:
            file_id = file.file_unique_id
        except Exception:
            try:
                file_id = file.file_id
            except Exception:
                # Skip this file if both IDs are unavailable
                continue 
        if file_id in MESSAGES:
           DUPLICATE.append(message.id)
        else:
           MESSAGES.append(file_id)
        total += 1
        if total %10000 == 0:
           await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
        if len(DUPLICATE) >= 100:
           await bot.delete_messages(chat_id, DUPLICATE)
           deleted += 100
           await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
           DUPLICATE = []
     if DUPLICATE:
        await bot.delete_messages(chat_id, DUPLICATE)
        deleted += len(DUPLICATE)
   except Exception as e:
       temp.lock[user_id] = False
       error_msg = f"**ERROR in Unequify Process**\n`{str(e)}`"
       logger.error(f"Unequify error for user {user_id}: {str(e)}")
       
       # Send error notification to log channel
       try:
           notify = NotificationManager(client)
           await notify.notify_error(user_id, "Unequify Process Failed", str(e))
       except Exception as notify_err:
           logger.error(f"Failed to send error notification: {notify_err}")
       
       await sts.edit(error_msg)
       return await bot.stop()
   temp.lock[user_id] = False
   await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"), reply_markup=COMPLETED_BTN)
   
   # Send completion notification to log channel
   try:
       notify = NotificationManager(client)
       await notify.notify_user_action(user_id, "Completed Unequify Process", f"Total: {total}, Deleted: {deleted}")
   except Exception as notify_err:
       logger.error(f"Failed to send unequify completion notification: {notify_err}")
   
   logger.info(f"Unequify completed for user {user_id}: Total={total}, Deleted={deleted}")
   await bot.stop()
   
