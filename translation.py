import os
from config import Config

class Translation(object):
  START_TXT = """<b>ʜᴇʟʟᴏ {}</b>

<i>ɪ'ᴍ ᴀ <b>ᴘᴏᴡᴇʀғᴜʟʟ</b> ᴀᴜᴛᴏ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ

ɪ ᴄᴀɴ ғᴏʀᴡᴀʀᴅ ᴀʟʟ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴏɴᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀɴɴᴇʟ</i> <b>➜ ᴡɪᴛʜ ᴍᴏʀᴇ ғᴇᴀᴛᴜʀᴇs.
ᴄʟɪᴄᴋ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴋɴᴏᴡ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ᴍᴇ</b>"""


  HELP_TXT = """<b><u>🔆 HELP</b></u>

<u>**📚 Essential Commands:**</u>
<b>⏣ __/start - Start bot and show main menu__ 
⏣ __/trial - Get 3-day premium trial (once per year)__
⏣ __/forward - Start message forwarding process__
⏣ __/settings - Configure your bot settings__
⏣ __/myplan - Check your subscription status__
⏣ __/commands - See all available commands__
⏣ __/info - Get your account information__
⏣ __/verify - Verify payment for premium__
⏣ __/reset - Reset your bot configurations__</b>

<u>**👑 Admin Commands:**</u>
<b>⏣ __/users - List all registered users__
⏣ __/speedtest - Network speed test__
⏣ __/system - System information__
⏣ __/broadcast - Send message to all users__</b>

<b><u>💢 Bot Features:</b></u>
<b>► __Forward messages from any channel to your channel__
► __Custom captions and buttons for forwarded messages__
► __Support for restricted and private chats__
► __Skip duplicate messages automatically__
► __Filter messages by type, size, and keywords__
► __FTM Mode with source link tracking (Pro plan)__
► __3-day free trial with unlimited forwarding__
► __Real-time system monitoring and speed tests__
► __Premium plans with unlimited forwarding__</b>

<b>💎 Use /trial for 3-day free premium trial!</b>
"""

  HOW_USE_TXT = """<b><u>⚠️ Before Forwarding:</b></u>
<b>► __add a bot or userbot__
► __add atleast one to channel__ `(your bot/userbot must be admin in there)`
► __You can add chats or bots by using /settings__
► __if the **From Channel** is private your userbot must be member in there or your bot must need admin permission in there also__
► __Then use /forward to forward messages__</b>"""

  ABOUT_TXT = """<b>╭──────❰ 🤖 Bot Details ❱──────〄
│ 
│ 🤖 Mʏ Nᴀᴍᴇ : <a href=https://t.me/Auto_Forward3_Bot>Auto 𝙵𝙾𝚁𝚆𝙰𝚁𝙳 𝙱𝙾𝚃</a>
│ 👨‍💻 ᴅᴇᴠᴘʟᴏᴇʀ : <a href=https://t.me/Hidden_Xman>Hidden Xman</a>
│ 🤖 ᴜᴘᴅᴀᴛᴇ  : <a href=https://t.me/Hidden_Xman>Hidden Xman</a>
│ 📡 ʜᴏsᴛ ᴏɴ : <a href=https://heroku.com.in/>𝙷𝙴𝚁𝙾𝙺𝚄</a>
│ 🗣️ ʟᴀɴɢᴜᴀɢᴇ  : ᴘʏᴛʜᴏɴ 3 {python_version}
│ 📚 ʟɪʙʀᴀʀʏ  : ᴘʏʀᴏɢʀᴀᴍ  
╰────────────────────⍟</b>"""

  STATUS_TXT = """<b>╭──────❪ 🤖 Bot Status ❫─────⍟
│
├👨 ᴜsᴇʀs  : {}
│
├🤖 ʙᴏᴛs : {}
│
├📣 ᴄʜᴀɴɴᴇʟ  : {} 
╰───────────────────⍟</b>""" 

  FROM_MSG = "<b>❪ SET SOURCE CHAT ❫\n\nForward the last message or last message link of source chat.\n/cancel - cancel this process</b>"
  TO_MSG = "<b>❪ CHOOSE TARGET CHAT ❫\n\nChoose your target chat from the given buttons.\n/cancel - Cancel this process</b>"
  SKIP_MSG = "<b>❪ SET MESSAGE SKIPING NUMBER ❫</b>\n\n<b>Skip the message as much as you enter the number and the rest of the message will be forwarded\nDefault Skip Number =</b> <code>0</code>\n<code>eg: You enter 0 = 0 message skiped\n You enter 5 = 5 message skiped</code>\n/cancel <b>- cancel this process</b>"
  CANCEL = "<b>Process Cancelled Succefully !</b>"
  BOT_DETAILS = "<b><u>📄 BOT DETAILS</b></u>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ BOT ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"
  USER_DETAILS = "<b><u>📄 USERBOT DETAILS</b></u>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ USER ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"  

  TEXT = """<b>╭────❰ <u>Forwarded Status</u> ❱────❍
┃
┣⊸<b>📋 ᴛᴏᴛᴀʟ ᴍsɢs :</b> <code>{}</code>
┣⊸<b>🕵 ғᴇᴛᴄʜᴇᴅ ᴍsɢ :</b> <code>{}</code>
┣⊸<b>✅ sᴜᴄᴄᴇғᴜʟʟʏ ғᴡᴅ :</b> <code>{}</code>
┣⊸<b>👥 ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴍsɢ :</b> <code>{}</code>
┣⊸<b>🗑️ ᴅᴇʟᴇᴛᴇᴅ/ғɪʟᴛᴇʀᴇᴅ :</b> <code>{}</code>
┣⊸<b>🪆 sᴋɪᴘᴘᴇᴅ ᴍsɢ :</b> <code>{}</code>
┣⊸<b>📊 sᴛᴀᴛᴜs :</b> <code>{}</code>
┣⊸<b>⏳ ᴘʀᴏɢʀᴇss :</b> <code>{}</code> %
┣⊸<b>⏰ ᴇᴛᴀ :</b> <code>{}</code>
┃
╰────⌊ <b>{}</b> ⌉───❍</b>"""

  TEXT1 = """<b>╭─❰ <u>Forwarded Status</u> ❱─❍
┃
┣⊸🕵Feched 𝙈𝙨𝙜 : {}
┣⊸✅𝙎𝙪𝙘𝙘𝙚𝙛𝙪𝙡𝙮 𝙁𝙬𝙙 : {}
┣⊸👥𝘿𝙪𝙥𝙡𝙞𝙘𝙖𝙩𝙚 𝙈𝙨𝙜: {}
┣⊸🗑𝘿𝙚𝙡𝙚𝙩𝙚𝙙 𝙈𝙨𝙜: {}
┣⊸🪆𝙎𝙠𝙞𝙥𝙥𝙚𝙙 : {}
┣⊸📊𝙎𝙩𝙖𝙩𝙨 : {}
┣⊸⏳𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨 : {}
┣⊸𝙀𝙏𝘼 : {}
┃
╰─⌊ {} ⌉─❍</b>"""

  DOUBLE_CHECK = """<b><u>DOUBLE CHECKING ⚠️</b></u>
<code>Before forwarding the messages Click the Yes button only after checking the following</code>

<b>★ YOUR BOT:</b> [{botname}](t.me/{botuname})
<b>★ FROM CHANNEL:</b> `{from_chat}`
<b>★ TO CHANNEL:</b> `{to_chat}`
<b>★ SKIP MESSAGES:</b> `{skip}`

<i>° [{botname}](t.me/{botuname}) must be admin in **TARGET CHAT**</i> (`{to_chat}`)
<i>° If the **SOURCE CHAT** is private your userbot must be member or your bot must be admin in there also</b></i>

<b>If the above is checked then the yes button can be clicked</b>"""

  # Premium System Messages
  @staticmethod
  def get_premium_limit_msg():
    from config import Config
    return f"""<b>🚫 Monthly Limit Reached!</b>

<b>Free users are limited to 1 process per month.</b>

<b>💎 Upgrade to Premium for unlimited access!</b>

<b>📋 Available Plans:</b>
• <b>Plus Plan:</b> ₹299/month - Unlimited forwarding
• <b>Pro Plan:</b> ₹549/month - Unlimited + FTM mode + Priority support

<b>💳 Payment UPI ID:</b> <code>{Config.UPI_ID}</code>

<b>How to upgrade:</b>
1. Choose your plan and send payment to <code>{Config.UPI_ID}</code>
2. Take screenshot of payment
3. Send screenshot with <code>/verify</code> 
4. Wait for admin approval

<b>Your current usage:</b> 1/1 processes used this month
<b>Next reset:</b> 1st of next month"""

  VERIFY_USAGE_MSG = """<b>❌ Invalid Usage!</b>

<b>Please reply to your payment screenshot with /verify command.</b>

<b>Example:</b>
1. Send your payment screenshot
2. Reply to that screenshot with <code>/verify</code>"""

  VERIFY_SUCCESS_MSG = """<b>✅ Payment Screenshot Submitted!</b>

<b>Your payment verification has been submitted to admins for review.</b>

<b>⏳ Please wait for admin approval.</b>
<b>💬 You will be notified once your payment is verified.</b>

<b>Verification ID:</b> <code>{verification_id}</code>"""

  PAYMENT_APPROVED_MSG = """<b>🎉 Payment Approved!</b>

<b>✅ Your payment has been verified and approved!</b>
<b>💎 You now have Premium access for 30 days.</b>

<b>Premium Benefits:</b>
• Unlimited forwarding processes
• Priority support
• All premium features unlocked

<b>Use /myplan to check your subscription details.</b>"""

  PAYMENT_REJECTED_MSG = """<b>❌ Payment Rejected</b>

<b>Your payment verification has been rejected.</b>

<b>Possible reasons:</b>
• Invalid payment screenshot
• Incorrect amount
• Payment not found
• Duplicate submission

<b>Please verify your payment and submit again with /verify</b>
<b>Or contact support for assistance.</b>"""

  PREMIUM_GRANTED_MSG = """<b>🎉 Premium Access Granted!</b>

<b>✅ You have been granted Premium access for {days} days!</b>
<b>💎 Granted by: {admin_name}</b>

<b>Premium Benefits:</b>
• Unlimited forwarding processes
• Priority support
• All premium features unlocked

<b>Expires:</b> {expires_date} UTC
<b>Use /myplan to check your subscription details.</b>"""

  PREMIUM_REMOVED_MSG = """<b>❌ Premium Access Removed</b>

<b>Your premium access has been removed by an admin.</b>
<b>Removed by:</b> {admin_name}

<b>You are now on the free plan with monthly limits.</b>
<b>💎 To get premium again, use /plan to see available plans</b>"""

  @staticmethod
  def get_plan_info_msg():
    from config import Config
    return f"""<b>💎 Premium Plans</b>

<b>🆓 Free Plan</b>
• 1 forwarding process per month
• Basic support
• Standard features

<b>🎁 3-Day Trial (Once per year)</b>
• ✅ Unlimited forwarding for 3 days
• ✅ All premium features (except FTM mode)
• ✅ Use /trial command or click trial button
• ✅ Available once per calendar year

<b>✨ Plus Plan - ₹199/15d, ₹299/30d</b>
• ✅ Unlimited forwarding processes
• ✅ All basic features
• ✅ Standard support

<b>🏆 Pro Plan - ₹299/15d, ₹549/30d</b>
• ✅ Unlimited forwarding processes
• ✅ FTM mode with source tracking
• ✅ Priority support
• ✅ All premium features

<b>💳 How to Subscribe:</b>
1. Send payment to <code>{Config.UPI_ID}</code>
2. Take screenshot of payment confirmation
3. Send screenshot with <code>/verify [plan] [duration]</code>
4. Wait for admin approval (usually within 10 minutes)

<b>💡 Tips:</b>
• Try 3-day trial first with /trial
• Include your username in payment reference
• Keep payment screenshot clear and complete
• Contact support if you need help

<b>📊 Check your current plan with /myplan</b>"""

  CHAT_STARTED_MSG = """<b>💬 Chat Session Started</b>

<b>Target User:</b> {user_info}
<b>User ID:</b> <code>{user_id}</code>
<b>Session ID:</b> <code>{session_id}</code>

<b>💡 Now send any message and it will be forwarded to the user.</b>
<b>🔚 Use /endchat to end the session.</b>"""

  ADMIN_CHAT_NOTIFY_MSG = """<b>💬 Admin Chat Session</b>

<b>An admin has started a chat session with you.</b>
<b>Admin:</b> {admin_name}

<b>You can now chat directly with the admin!</b>"""

  # Force Subscribe Messages
  FORCE_SUBSCRIBE_MSG = """<b>🔒 Join Required Channels!</b>

<b>To use this bot, you must join our required channels first.</b>

<b>📢 Please join all the channels below by clicking the buttons.</b>

<b>After joining all channels, click '✅ Check Subscription' to continue.</b>"""

  # Bot and Channel Messages
  NO_BOT_ADDED_MSG = """<b>❌ No Bot Added!</b>

<b>You haven't added any bot yet. Please add a bot using /settings first!</b>

<b>Steps:</b>
1. Go to /settings
2. Click on 🤖 Bots
3. Add your bot token
4. Try forwarding again"""

  NO_CHANNELS_MSG = """<b>❌ No Target Channel!</b>

<b>Please set a target channel in /settings before forwarding.</b>

<b>Steps:</b>
1. Go to /settings
2. Click on 🏷 Channels
3. Add your target channel
4. Try forwarding again"""

  WRONG_CHANNEL_MSG = """<b>❌ Wrong Channel Selected!</b>

<b>Please select a valid channel from the list.</b>"""

  # Link and Message Validation
  INVALID_LINK_MSG = """<b>❌ Invalid Link!</b>

<b>Please provide a valid Telegram message link.</b>

<b>Format:</b> <code>https://t.me/channel/messageid</code>"""

  INVALID_LINK_SPECIFIED_MSG = """<b>❌ Invalid Link Specified!</b>

<b>The link you provided is not valid. Please check and try again.</b>"""

  INVALID_MSG = """<b>❌ Invalid Message!</b>

<b>Please provide a valid message or link.</b>"""

  FORWARDED_FROM_GROUP_MSG = """<b>⚠️ Forwarded from Group!</b>

<b>This may be a forwarded message from a group sent by an anonymous admin.</b>

<b>Instead of this, please send the last message link from the group.</b>"""

  # Settings Messages
  SETTINGS_MAIN_MSG = """<b>⚙️ SETTINGS ⚙️</b>

<b>Configure your bot settings using the buttons below:</b>

🤖 <b>Bots:</b> Manage your bot tokens
🏷 <b>Channels:</b> Manage target channels  
🖋️ <b>Caption:</b> Custom message captions
🗃 <b>MongoDB:</b> Database configuration
🕵‍♀ <b>Filters:</b> Message type filters
⏹ <b>Button:</b> Custom inline buttons
🔥 <b>FTM Mode:</b> Advanced forwarding
🧪 <b>Extra Settings:</b> Additional options"""

  BOT_TOKEN_ADDED_MSG = "<b>✅ Bot token successfully added!</b>"
  SESSION_ADDED_MSG = "<b>✅ Session string successfully added!</b>"
  PHONE_BOT_ADDED_MSG = "<b>✅ Phone bot successfully added!</b>"

  BOT_DETAILS = """<b>🤖 BOT DETAILS</b>

<b>Name:</b> {0}
<b>ID:</b> <code>{1}</code>
<b>Username:</b> @{2}"""

  USER_DETAILS = """<b>👤 USER DETAILS</b>

<b>Name:</b> {0}
<b>ID:</b> <code>{1}</code>
<b>Username:</b> @{2}"""

  CHANNEL_ADDED_MSG = """<b>✅ Channel Added!</b>

<b>Successfully updated</b>"""

  CHANNEL_ALREADY_EXISTS_MSG = """<b>⚠️ Channel Already Added!</b>

<b>This channel already exists in your list</b>"""

  NOT_FORWARD_MESSAGE_MSG = """<b>❌ Not a Forward Message!</b>

<b>This is not a forward message</b>"""

  BOT_REMOVED_MSG = """<b>✅ Bot Removed!</b>

<b>Successfully updated</b>"""

  CHANNEL_REMOVED_MSG = """<b>✅ Channel Removed!</b>

<b>Successfully updated</b>"""

  CAPTION_DELETED_MSG = """<b>✅ Caption Deleted!</b>

<b>Successfully updated</b>"""

  PROCESS_CANCELLED_MSG = """<b>❌ Process Cancelled!</b>

<b>Process canceled</b>"""

  WRONG_FILLING_MSG = """<b>❌ Wrong Filling!</b>

<b>Wrong filling {error} used in your caption. Change it</b>"""

  CAPTION_UPDATED_MSG = """<b>✅ Caption Updated!</b>

<b>Successfully updated</b>"""

  BUTTON_ADDED_MSG = """<b>✅ Button Added!</b>

<b>Successfully button added</b>"""

  INVALID_BUTTON_MSG = """<b>❌ Invalid Button!</b>

<b>Invalid button format</b>"""

  BUTTON_DELETED_MSG = """<b>✅ Button Deleted!</b>

<b>Successfully button deleted</b>"""

  DATABASE_URL_ADDED_MSG = """<b>✅ Database URL Added!</b>

<b>Successfully database url added</b>"""

  INVALID_MONGODB_URL_MSG = """<b>❌ Invalid MongoDB URL!</b>

<b>Invalid MongoDB URL</b>"""

  DATABASE_URL_DELETED_MSG = """<b>✅ Database URL Deleted!</b>

<b>Successfully your database url deleted</b>"""

  SUCCESSFULLY_UPDATED_MSG = """<b>✅ Successfully Updated!</b>

<b>Successfully updated</b>"""

  TIMEOUT_MSG = """<b>⏰ Process Timeout!</b>

<b>Process has been automatically cancelled</b>"""

  # Trial System Messages
  TRIAL_ACTIVATED_MSG = """<b>🎉 3-Day Trial Activated!</b>

<b>✅ You now have unlimited forwarding for 3 days!</b>

<b>Trial Benefits:</b>
• ✅ Unlimited forwarding processes
• ✅ All premium features (except FTM mode)
• ✅ Priority support

<b>⏰ Expires:</b> {expires_date}

<b>💡 Use /forward to start forwarding messages!</b>
<b>📊 Check status anytime with /myplan</b>"""

  TRIAL_ALREADY_USED_MSG = """<b>❌ Trial Already Used!</b>

<b>You have already used your free trial this year.</b>
<b>Trial is available once per calendar year.</b>

<b>💎 Check our premium plans with /plan</b>"""

  TRIAL_CONFIRMATION_MSG = """<b>🎁 Activate Free Trial?</b>

<b>✅ 3 days unlimited forwarding</b>
<b>✅ All premium features (except FTM mode)</b>
<b>✅ Priority support</b>

<b>⚠️ Available once per year only!</b>

<b>Do you want to activate your free trial now?</b>"""

  COMMANDS_LIST_MSG = """<b>📋 Available Commands</b>

<b>🔥 Essential Commands:</b>
• <code>/start</code> - Start bot and show main menu
• <code>/help</code> - Get detailed help and instructions
• <code>/forward</code> - Start message forwarding process
• <code>/settings</code> - Configure your bot settings
• <code>/myplan</code> - Check your subscription status
• <code>/info</code> - Get your account information
• <code>/reset</code> - Reset your bot configurations

<b>💎 Premium Features:</b>
• <code>/trial</code> - Get 3-day free trial
• <code>/verify</code> - Verify payment for premium plans
• <code>/plan</code> - View available premium plans

<b>👑 Admin Commands:</b>
• <code>/users</code> - List all registered users
• <code>/broadcast</code> - Send message to all users
• <code>/speedtest</code> - Network speed test
• <code>/system</code> - System information

<b>💡 Pro Tip:</b> Use /trial for instant premium access!"""