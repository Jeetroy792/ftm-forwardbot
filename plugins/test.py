import os
import re
import sys
import typing
import asyncio
import logging
from database import db
from config import Config, temp
from pyrogram import Client, filters
from pyrogram.raw.all import layer
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from pyrogram.errors import FloodWait
from config import Config
from translation import Translation

from typing import Union, Optional, AsyncGenerator
from pyrogram import Client, filters

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global storage for waiting messages
waiting_messages = {}

# Message handler for waiting responses
@Client.on_message(filters.private & filters.text & ~filters.command(['start', 'help', 'settings', 'trial', 'premium', 'broadcast']))
async def handle_waiting_messages(client, message):
    """Handle messages for users waiting for input"""
    user_id = message.from_user.id
    
    # Check if user is in waiting state
    if user_id in waiting_messages:
        future = waiting_messages[user_id]
        if not future.done():
            try:
                future.set_result(message)
                logger.info(f"Message received from waiting user {user_id}: {message.text[:50]}...")
            except Exception as e:
                logger.error(f"Error setting result for user {user_id}: {e}")
        
        # Clean up the waiting message entry
        try:
            if user_id in waiting_messages:
                del waiting_messages[user_id]
        except KeyError:
            pass

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")
BOT_TOKEN_TEXT = "<b>1) create a bot using @BotFather\n2) Then you will get a message with bot token\n3) Forward that message to me</b>"
SESSION_STRING_SIZE = 351

async def get_configs(user_id):
    """Get user configurations from database"""
    try:
        user_data = await db.get_configs(user_id)
        if not user_data:
            # Return default config if user not found
            return {
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
                'caption': None,
                'forward_tag': False,
                'protect': False,
                'duplicate': True,
                'file_size': 0,
                'size_limit': False,
                'extension': [],
                'keywords': [],
                'button': None,
                'db_uri': None,
                'ftm_mode': False
            }

        # Ensure all required keys exist with proper defaults
        if 'ftm_mode' not in user_data:
            user_data['ftm_mode'] = False
        if 'keywords' not in user_data:
            user_data['keywords'] = []
        if 'extension' not in user_data:
            user_data['extension'] = []
        if 'file_size' not in user_data:
            user_data['file_size'] = 0
        if 'size_limit' not in user_data:
            user_data['size_limit'] = False
        if 'duplicate' not in user_data:
            user_data['duplicate'] = True
        if 'protect' not in user_data:
            user_data['protect'] = False
        if 'forward_tag' not in user_data:
            user_data['forward_tag'] = False
        if 'caption' not in user_data:
            user_data['caption'] = None
        if 'button' not in user_data:
            user_data['button'] = None
        if 'db_uri' not in user_data:
            user_data['db_uri'] = None

        # Ensure filters exist and have all required message types
        if 'filters' not in user_data:
            user_data['filters'] = {
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
            }
        else:
            # Ensure all filter types exist
            default_filters = {
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
            }
            for key, default_value in default_filters.items():
                if key not in user_data['filters']:
                    user_data['filters'][key] = default_value

        return user_data
    except Exception as e:
        logger.error(f"Error getting configs for user {user_id}: {e}")
        # Return default config on error
        return {
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
            'caption': None,
            'forward_tag': False,
            'protect': False,
            'duplicate': True,
            'file_size': 0,
            'size_limit': False,
            'extension': [],
            'keywords': [],
            'button': None,
            'db_uri': None,
            'ftm_mode': False
        }

async def update_configs(user_id, key, value):
    """Update user configuration in database"""
    try:
        current = await get_configs(user_id)
        if key in ['caption', 'duplicate', 'db_uri', 'forward_tag', 'protect', 'file_size', 'size_limit', 'extension', 'keywords', 'button', 'ftm_mode']:
            current[key] = value
        else:
            current['filters'][key] = value

        await db.update_configs(user_id, current)
        return True
    except Exception as e:
        logger.error(f"Error updating config for user {user_id}: {e}")
        return False

async def start_clone_bot(FwdBot, data=None):
    await FwdBot.start()

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
        search: str = None,
        filter: "types.TypeMessagesFilter" = None,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially."""
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

    # Bind the method to the instance properly
    import types
    FwdBot.iter_messages = types.MethodType(iter_messages, FwdBot)
    return FwdBot

class CLIENT:
    def __init__(self):
        self.api_id = Config.API_ID
        self.api_hash = Config.API_HASH

    def client(self, data, user=None):
        if user == None and data.get('is_bot') == False:
            return Client("USERBOT", self.api_id, self.api_hash, session_string=data.get('session'))
        elif user == True:
            return Client("USERBOT", self.api_id, self.api_hash, session_string=data)
        elif user != False:
            data = data.get('token')
        return Client("BOT", self.api_id, self.api_hash, bot_token=data, in_memory=True)

    async def add_bot(self, client, query):
        """Add bot token using proper message handling"""
        try:
            user_id = query.from_user.id

            # Request bot token
            prompt_msg = await client.send_message(
                user_id, 
                "<b>❪ SET BOT TOKEN ❫\n\nSend your bot token\n/cancel - cancel this process</b>"
            )

            # Wait for user response using message handler
            response = await self._wait_for_message(client, user_id, timeout=300)

            if not response or response.text == "/cancel":
                if response:
                    await response.delete()
                await prompt_msg.delete()
                return False

            bot_token = response.text.strip()
            await response.delete()
            await prompt_msg.delete()

            # Validate bot token format
            if not bot_token or len(bot_token) < 20 or ':' not in bot_token:
                await client.send_message(user_id, "<b>❌ Invalid bot token format!</b>")
                return False

            # Test the bot token
            try:
                test_bot = Client("test_bot", self.api_id, self.api_hash, bot_token=bot_token, in_memory=True)
                await test_bot.start()
                bot_info = await test_bot.get_me()
                await test_bot.stop()

                # Save to database
                bot_data = {
                    'user_id': user_id,
                    'token': bot_token,
                    'name': bot_info.first_name,
                    'username': bot_info.username or 'unknown',
                    'id': bot_info.id,
                    'is_bot': True
                }
                await db.add_bot(bot_data)
                return True

            except Exception as test_error:
                await client.send_message(user_id, f"<b>❌ Invalid bot token: {str(test_error)}</b>")
                return False

        except Exception as e:
            logger.error(f"Error adding bot: {e}")
            return False

    async def add_session(self, client, query):
        """Add session string using proper message handling"""
        try:
            user_id = query.from_user.id

            prompt_msg = await client.send_message(
                user_id,
                "<b>❪ SET SESSION STRING ❫\n\nSend your session string\n/cancel - cancel this process</b>"
            )

            response = await self._wait_for_message(client, user_id, timeout=300)

            if not response or response.text == "/cancel":
                if response:
                    await response.delete()
                await prompt_msg.delete()
                return False

            session = response.text.strip()
            await response.delete()
            await prompt_msg.delete()

            if not session or len(session) < 50:
                await client.send_message(user_id, "<b>❌ Invalid session string!</b>")
                return False

            # Test the session string
            try:
                test_client = Client("test_session", self.api_id, self.api_hash, session_string=session, in_memory=True)
                await test_client.start()
                user_info = await test_client.get_me()
                await test_client.stop()

                # Save session
                bot_data = {
                    'user_id': user_id,
                    'session': session,
                    'name': user_info.first_name,
                    'username': user_info.username or 'unknown',
                    'id': user_info.id,
                    'is_bot': False
                }
                await db.add_bot(bot_data)
                return True

            except Exception as test_error:
                await client.send_message(user_id, f"<b>❌ Invalid session string: {str(test_error)}</b>")
                return False

        except Exception as e:
            logger.error(f"Error adding session: {e}")
            return False

    async def add_phone_login(self, client, query):
        """Add phone login using proper message handling"""
        try:
            user_id = query.from_user.id

            prompt_msg = await client.send_message(
                user_id,
                "<b>❪ PHONE LOGIN ❫\n\nSend your phone number with country code (e.g., +1234567890)\n/cancel - cancel this process</b>"
            )

            response = await self._wait_for_message(client, user_id, timeout=300)

            if not response or response.text == "/cancel":
                if response:
                    await response.delete()
                await prompt_msg.delete()
                return False

            phone = response.text.strip()
            await response.delete()
            await prompt_msg.delete()

            if not phone or not phone.startswith('+'):
                await client.send_message(user_id, "<b>❌ Please provide phone number with country code!</b>")
                return False

            # Create client with phone number
            client_phone = Client("USERBOT_PHONE", self.api_id, self.api_hash, phone_number=phone, in_memory=True)
            try:
                await client_phone.connect()

                # Send code
                sent_code = await client_phone.send_code(phone)

                # Get verification code
                code_prompt = await client.send_message(
                    user_id,
                    "<b>Send the verification code you received from Telegram.\n\n⚠️ Format: If code is 12345, send it as: FTM12345\n\n/cancel - cancel this process</b>"
                )

                code_response = await self._wait_for_message(client, user_id, timeout=300)

                if not code_response or code_response.text == "/cancel":
                    if code_response:
                        await code_response.delete()
                    await code_prompt.delete()
                    await client_phone.disconnect()
                    return False

                verification_code = code_response.text.strip()
                await code_response.delete()
                await code_prompt.delete()

                # Extract actual code if it has FTM prefix
                if verification_code.upper().startswith('FTM'):
                    verification_code = verification_code[3:]

                # Sign in
                try:
                    await client_phone.sign_in(phone, sent_code.phone_code_hash, verification_code)
                except Exception as e:
                    error_str = str(e).lower()
                    if "two-step verification" in error_str or "password" in error_str:
                        # Get 2FA password
                        password_prompt = await client.send_message(
                            user_id,
                            "<b>Two-step verification is enabled.\n\nSend your 2FA password\n\n/cancel - cancel this process</b>"
                        )

                        password_response = await self._wait_for_message(client, user_id, timeout=300)

                        if not password_response or password_response.text == "/cancel":
                            if password_response:
                                await password_response.delete()
                            await password_prompt.delete()
                            await client_phone.disconnect()
                            return False

                        await client_phone.check_password(password_response.text)
                        await password_response.delete()
                        await password_prompt.delete()
                    else:
                        raise e

                # Export session string
                session_string = await client_phone.export_session_string()
                user_info = await client_phone.get_me()
                await client_phone.disconnect()

                # Save session
                bot_data = {
                    'user_id': user_id,
                    'session': session_string,
                    'name': user_info.first_name,
                    'username': user_info.username or 'unknown',
                    'id': user_info.id,
                    'is_bot': False
                }
                await db.add_bot(bot_data)

                await client.send_message(
                    user_id,
                    f"<b>✅ Successfully logged in!</b>\n\n<b>Account:</b> {user_info.first_name}\n<b>Username:</b> @{user_info.username if user_info.username else 'None'}\n<b>ID:</b> {user_info.id}"
                )
                return True

            except Exception as e:
                try:
                    await client_phone.disconnect()
                except:
                    pass
                await client.send_message(user_id, f"<b>LOGIN ERROR:</b> {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error adding phone login: {e}")
            return False

    async def _wait_for_message(self, client, user_id, timeout=300):
        """Wait for a message from specific user"""
        try:
            logger.info(f"Setting up message wait for user {user_id}")
            
            # Clean up any existing waiting message for this user
            if user_id in waiting_messages:
                old_future = waiting_messages[user_id]
                if not old_future.done():
                    try:
                        old_future.cancel()
                    except:
                        pass
                try:
                    del waiting_messages[user_id]
                except KeyError:
                    pass

            # Create a new future
            future = asyncio.Future()
            waiting_messages[user_id] = future
            logger.info(f"Created future for user {user_id}, total waiting: {len(waiting_messages)}")

            try:
                # Wait for the message with timeout
                logger.info(f"Waiting for message from user {user_id} (timeout: {timeout}s)")
                message = await asyncio.wait_for(future, timeout=timeout)
                logger.info(f"Received message from user {user_id}: {message.text if message else 'None'}")
                return message
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for message from user {user_id}")
                return None
            except asyncio.CancelledError:
                logger.info(f"Message wait cancelled for user {user_id}")
                return None
            except Exception as wait_error:
                logger.error(f"Error during wait for user {user_id}: {wait_error}")
                return None
            finally:
                # Clean up
                try:
                    if user_id in waiting_messages:
                        del waiting_messages[user_id]
                        logger.info(f"Cleaned up waiting message for user {user_id}")
                except KeyError:
                    pass

        except Exception as e:
            logger.error(f"Error waiting for message from user {user_id}: {e}", exc_info=True)
            # Clean up on error
            try:
                if user_id in waiting_messages:
                    del waiting_messages[user_id]
            except KeyError:
                pass
            return None

def parse_buttons(text, markup=True):
    """Parse button text into inline keyboard buttons"""
    if not text or not text.strip():
        return [] if not markup else None

    try:
        buttons = []
        lines = text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match pattern: [Button Text][buttonurl:URL]
            match = re.search(r'\[([^\[\]]+)\]\s*\[buttonurl:\s*([^\[\]]+)\]', line, re.IGNORECASE)
            if match:
                button_text = match.group(1).strip()
                button_url = match.group(2).strip()

                # Validate button text is not empty
                if not button_text:
                    continue

                # Basic URL validation and formatting
                if not button_url:
                    continue

                # Format URL properly
                if not button_url.startswith(('http://', 'https://', 'tg://')):
                    if button_url.startswith('@'):
                        button_url = 'https://t.me/' + button_url[1:]
                    elif button_url.startswith(('t.me/', 'telegram.me/')):
                        button_url = 'https://' + button_url
                    elif '.' not in button_url:
                        # Assume it's a telegram username without @
                        button_url = 'https://t.me/' + button_url.replace('@', '')
                    else:
                        # Add https if it looks like a domain
                        if not button_url.startswith('www.'):
                            button_url = 'https://' + button_url

                buttons.append([InlineKeyboardButton(button_text, url=button_url)])

        return InlineKeyboardMarkup(buttons) if markup and buttons else buttons

    except Exception as e:
        logger.error(f"Error parsing buttons: {e}")
        return [] if not markup else None