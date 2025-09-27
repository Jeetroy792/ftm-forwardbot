from os import environ 
from config import Config
import motor.motor_asyncio
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import logging
from pyrogram.enums import ChatMemberStatus

# Set up logger
logger = logging.getLogger(__name__)

async def mongodb_version():
    x = MongoClient(Config.DATABASE_URI)
    mongodb_version = x.server_info()['version']
    return mongodb_version

class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.bot = self.db.bots
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels
        self.queue_col = self.db.queue  # For crash recovery queue
        self.premium_col = self.db.premium_users  # Premium users collection
        self.payment_col = self.db.payment_verifications  # Payment verification collection
        self.usage_col = self.db.usage_tracking  # Monthly usage tracking
        self.admin_chat_col = self.db.admin_chats  # Admin chat sessions
        self.contact_requests_col = self.db.contact_requests  # Contact requests collection 
        self.chat_requests_col = self.db.chat_requests  # Chat requests collection 
        self.trial_col = self.db.trial_usage # Trial usage collection
        self.referral_col = self.db.referrals  # Referral system collection
        self.alpha_config_col = self.db.alpha_configs  # FTM Alpha mode configuration collection

    def new_user(self, id, name):
        from datetime import datetime
        return dict(
            id = id,
            name = name,
            joined_date = datetime.utcnow(),
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            referral_code = None,  # User's own referral code
            referred_by = None,    # ID of user who referred them
            referral_completed = False,  # Whether their referral was completed (started bot + joined channels)
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        result = await self.col.insert_one(user)
        
        # Create referral code for new user
        referral_code = await self.create_referral_code(id)
        logger.info(f"Created referral code {referral_code} for new user {id}")
        
        return result

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)

    async def total_users_bots_count(self):
        bcount = await self.bot.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount

    async def total_channels(self):
        count = await self.chl.count_documents({})
        return count

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return await self.col.find({}).to_list(length=1000)

    async def get_user(self, user_id):
        """Get user data by user ID"""
        return await self.col.find_one({'id': int(user_id)})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        b_users = [user['id'] async for user in users]
        return b_users

    async def update_configs(self, id, configs):
        await self.col.update_one({'id': int(id)}, {'$set': {'configs': configs}})

    async def update_user_config(self, user_id, key, value):
        """Update a specific configuration key for a user"""
        try:
            # Get current configs
            current_configs = await self.get_configs(user_id)
            
            # Update the specific key
            current_configs[key] = value
            
            # Save back the entire config
            await self.update_configs(user_id, current_configs)
            return True
        except Exception as e:
            print(f"Error updating user config for user {user_id}, key {key}: {e}")
            return False

    async def get_configs(self, id):
        default = {
            'caption': None,
            'button': None,
            'duplicate': True,
            'db_uri': None,
            'forward_tag': False,
            'file_size': 0,
            'size_limit': None,
            'extension': None,
            'keywords': None,
            'ftm_mode': False,  # Now called FTM Delta mode
            'ftm_alpha_mode': False,  # New FTM Alpha mode for real-time forwarding
            'alpha_source_chat': None,  # Source channel for Alpha mode
            'alpha_target_chat': None,  # Target channel for Alpha mode
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
        user = await self.col.find_one({'id':int(id)})
        if user:
            return user.get('configs', default)
        return default 

    async def add_bot(self, datas):
       if not await self.is_bot_exist(datas['user_id']):
          await self.bot.insert_one(datas)

    async def remove_bot(self, user_id):
       await self.bot.delete_many({'user_id': int(user_id)})

    async def get_bot(self, user_id: int):
       bot = await self.bot.find_one({'user_id': user_id})
       return bot if bot else None

    async def is_bot_exist(self, user_id):
       bot = await self.bot.find_one({'user_id': user_id})
       return bool(bot)

    async def in_channel(self, user_id: int, chat_id: int) -> bool:
       channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
       return bool(channel)

    async def add_channel(self, user_id: int, chat_id: int, title, username):
       channel = await self.in_channel(user_id, chat_id)
       if channel:
         return False
       return await self.chl.insert_one({"user_id": user_id, "chat_id": chat_id, "title": title, "username": username})

    async def remove_channel(self, user_id: int, chat_id: int):
       channel = await self.in_channel(user_id, chat_id )
       if not channel:
         return False
       return await self.chl.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_channel_details(self, user_id: int, chat_id: int):
       return await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_user_channels(self, user_id: int):
       channels = self.chl.find({"user_id": int(user_id)})
       return [channel async for channel in channels]

    async def get_channel_info(self, channel_id):
        """Get channel information by ID"""
        try:
            # This would typically fetch from Telegram API
            # For now, return basic info
            return {'title': f'Channel {channel_id}', 'id': channel_id}
        except Exception:
            return None

    async def get_filters(self, user_id):
       filters = []
       filter = (await self.get_configs(user_id))['filters']
       for k, v in filter.items():
          if v == False:
            filters.append(str(k))
       return filters

    async def add_frwd(self, user_id):
       return await self.nfy.insert_one({'user_id': int(user_id)})

    async def rmve_frwd(self, user_id=0, all=False):
       data = {} if all else {'user_id': int(user_id)}
       return await self.nfy.delete_many(data)

    async def get_all_frwd(self):
       return self.nfy.find({})

    # Queue management for crash recovery
    async def add_queue_item(self, user_id, process_data):
        """Add a forwarding process to the queue"""
        queue_item = {
            'user_id': user_id,
            'status': 'active',
            'created_at': datetime.utcnow(),
            'process_data': process_data
        }
        result = await self.queue_col.insert_one(queue_item)
        return result.inserted_id

    async def update_queue_status(self, user_id, status):
        """Update queue status (active, completed, cancelled)"""
        return await self.queue_col.update_one(
            {'user_id': user_id, 'status': 'active'},
            {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
        )

    async def get_active_queues(self):
        """Get all active forwarding processes for crash recovery"""
        return await self.queue_col.find({'status': 'active'}).to_list(length=100)

    async def remove_completed_queues(self):
        """Clean up completed/cancelled queue items older than 1 day"""
        cutoff = datetime.utcnow() - timedelta(days=1)
        result = await self.queue_col.delete_many({
            'status': {'$in': ['completed', 'cancelled']},
            'updated_at': {'$lt': cutoff}
        })
        return result.deleted_count

    # Premium user management
    async def add_premium_user(self, user_id, plan_type="pro", duration_days=30, amount_paid=None):
        """Add a user to premium with three-tier support"""
        expires_at = datetime.utcnow() + timedelta(days=duration_days)

        premium_data = {
            'user_id': int(user_id),
            'plan_type': plan_type,  # 'free', 'plus', 'pro'
            'duration_days': duration_days,
            'amount_paid': amount_paid,
            'subscribed_at': datetime.utcnow(),
            'expires_at': expires_at,
            'is_active': True,
            'auto_renew': False,
            'features': self._get_plan_features(plan_type)
        }

        # Special handling for sudo lifetime subscriptions
        if amount_paid == "sudo_lifetime_subscription":
            premium_data['is_sudo_lifetime'] = True
            premium_data['expires_at'] = datetime.utcnow() + timedelta(days=365250)  # 999+ years
            
        # Remove existing premium record if any
        await self.premium_col.delete_many({'user_id': int(user_id)})
        return await self.premium_col.insert_one(premium_data)

    def _get_plan_features(self, plan_type):
        """Get features for a specific plan type"""
        from config import Config
        return Config.PLAN_FEATURES.get(plan_type, Config.PLAN_FEATURES['free'])

    async def remove_premium_user(self, user_id):
        """Remove a user from premium"""
        return await self.premium_col.delete_many({'user_id': int(user_id)})

    async def is_premium_user(self, user_id):
        """Check if user has active premium subscription"""
        user = await self.premium_col.find_one({
            'user_id': int(user_id),
            'is_active': True,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        
        # Special check for sudo lifetime subscriptions
        if not user:
            sudo_user = await self.premium_col.find_one({
                'user_id': int(user_id),
                'is_active': True,
                'is_sudo_lifetime': True
            })
            return bool(sudo_user)
            
        return bool(user)

    async def get_user_plan(self, user_id):
        """Get user's current plan type"""
        user = await self.premium_col.find_one({
            'user_id': int(user_id),
            'is_active': True,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        return user['plan_type'] if user else 'free'

    async def get_user_plan_features(self, user_id):
        """Get user's plan features"""
        user = await self.premium_col.find_one({
            'user_id': int(user_id),
            'is_active': True,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        if user:
            plan_type = user.get('plan_type', 'free')
            current_plan_features = self._get_plan_features(plan_type)
            stored_features = user.get('features', {})

            # Merge current plan features with stored features (current plan takes precedence for missing keys)
            merged_features = {**current_plan_features, **stored_features}

            # If features are missing/outdated, update them in database
            if stored_features != merged_features:
                await self.premium_col.update_one(
                    {'user_id': int(user_id)},
                    {'$set': {'features': merged_features}}
                )
                print(f"✅ Updated features for Pro user {user_id}: added missing keys")

            return merged_features
        return self._get_plan_features('free')

    async def can_use_ftm_mode(self, user_id):
        """Check if user can use FTM Delta mode (Pro plan only)"""
        features = await self.get_user_plan_features(user_id)
        return features.get('ftm_mode', False)
    
    async def can_use_ftm_alpha_mode(self, user_id):
        """Check if user can use FTM Alpha mode (pro plan required)"""
        user_plan = await self.get_user_plan(user_id)
        return user_plan in ['pro', 'plus'] or await self.is_premium_user(user_id)
    
    async def get_alpha_config(self, user_id):
        """Get FTM Alpha mode configuration for user"""
        config = await self.alpha_config_col.find_one({'user_id': int(user_id)})
        if not config:
            # Return default configuration
            return {
                'user_id': int(user_id),
                'enabled': False,
                'source_chat': None,
                'target_chat': None,
                'auto_forward': False
            }
        return config
    
    async def set_alpha_config(self, user_id, enabled=None, source_chat=None, target_chat=None, auto_forward=None):
        """Set FTM Alpha mode configuration for user"""
        update_data = {}
        if enabled is not None:
            update_data['enabled'] = enabled
        if source_chat is not None:
            update_data['source_chat'] = source_chat
        if target_chat is not None:
            update_data['target_chat'] = target_chat
        if auto_forward is not None:
            update_data['auto_forward'] = auto_forward
        
        return await self.alpha_config_col.update_one(
            {'user_id': int(user_id)},
            {'$set': update_data},
            upsert=True
        )

    async def get_forwarding_limit(self, user_id):
        """Get user's daily forwarding limit"""
        features = await self.get_user_plan_features(user_id)
        return features.get('forwarding_limit', 5)

    async def has_priority_support(self, user_id):
        """Check if user has priority support"""
        features = await self.get_user_plan_features(user_id)
        return features.get('priority_support', False)

    async def get_premium_user_details(self, user_id):
        """Get premium user details"""
        return await self.premium_col.find_one({'user_id': int(user_id)})

    async def get_premium_info(self, user_id):
        """Get premium user info (alias for get_premium_user_details)"""
        return await self.get_premium_user_details(user_id)

    async def get_user_usage(self, user_id):
        """Get user's total usage count"""
        daily_usage = await self.get_daily_usage(user_id)
        return daily_usage.get('processes', 0)

    async def get_days_remaining(self, user_id):
        """Get days remaining for premium subscription"""
        premium_info = await self.get_premium_user_details(user_id)
        if premium_info and premium_info.get('expires_at'):
            from datetime import datetime
            expires_at = premium_info['expires_at']
            if isinstance(expires_at, datetime):
                days_remaining = max(0, (expires_at - datetime.utcnow()).days)
                return days_remaining
        return 0

    async def get_monthly_usage(self, user_id):
        """Get user's usage for current month"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage = await self.usage_col.find_one({
            'user_id': int(user_id),
            'date': start_of_month
        })
        return usage if usage else {'user_id': int(user_id), 'date': start_of_month, 'processes': 0, 'trial_processes': 0}

    async def add_trial_processes(self, user_id, additional_processes=1):
        """Add trial processes to user's monthly limit (legacy method)"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Check if trial already activated this month
        existing = await self.usage_col.find_one({
            'user_id': int(user_id), 
            'date': start_of_month,
            'trial_activated': True
        })

        if existing:
            return False  # Trial already claimed this month

        await self.usage_col.update_one(
            {'user_id': int(user_id), 'date': start_of_month},
            {
                '$set': {
                    'trial_processes': additional_processes, 
                    'trial_activated': True, 
                    'trial_granted_at': datetime.utcnow()
                },
                '$setOnInsert': {'processes': 0}
            },
            upsert=True
        )
        return True  # Trial successfully granted

    async def activate_3day_trial(self, user_id):
        """Activate 3-day premium trial (once per year)"""
        current_year = datetime.utcnow().year

        # Check if user already used trial this year
        existing_trial = await self.premium_col.find_one({
            'user_id': int(user_id),
            'plan_type': '3day_trial',
            'trial_year': current_year
        })

        if existing_trial:
            return False, "Trial already used this year"

        # Check if user currently has premium
        if await self.is_premium_user(user_id):
            return False, "Already has premium access"

        # Grant 3-day premium trial
        expires_at = datetime.utcnow() + timedelta(days=3)

        trial_data = {
            'user_id': int(user_id),
            'plan_type': '3day_trial',
            'duration_days': 3,
            'amount_paid': 0,
            'subscribed_at': datetime.utcnow(),
            'expires_at': expires_at,
            'is_active': True,
            'auto_renew': False,
            'trial_year': current_year,
            'features': {
                'forwarding_limit': -1,  # unlimited
                'ftm_mode': False,  # No FTM mode in trial
                'priority_support': False,
                'unlimited_forwarding': True
            }
        }

        result = await self.premium_col.insert_one(trial_data)
        return True, "3-day trial activated successfully"

    async def can_use_trial(self, user_id):
        """Check if user can use 3-day trial (once per year)"""
        current_year = datetime.utcnow().year

        # Check if already used this year
        existing_trial = await self.premium_col.find_one({
            'user_id': int(user_id),
            'plan_type': '3day_trial',
            'trial_year': current_year
        })

        return existing_trial is None

    async def grant_trial(self, user_id):
        """Grant 3-day trial to user"""
        try:
            current_year = datetime.utcnow().year

            # Check if already used this year
            if not await self.can_use_trial(user_id):
                return False, "Trial already used this year"

            # Check if currently premium
            if await self.is_premium_user(user_id):
                return False, "Already has premium access"

            # Remove any existing premium records
            await self.premium_col.delete_many({'user_id': int(user_id)})

            # Grant 3-day trial
            expires_at = datetime.utcnow() + timedelta(days=3)

            trial_data = {
                'user_id': int(user_id),
                'plan_type': '3day_trial',
                'duration_days': 3,
                'amount_paid': 0,
                'subscribed_at': datetime.utcnow(),
                'expires_at': expires_at,
                'is_active': True,
                'auto_renew': False,
                'trial_year': current_year,
                'features': {
                    'forwarding_limit': -1,  # unlimited
                    'ftm_mode': False,  # No FTM mode in trial
                    'priority_support': True,
                    'unlimited_forwarding': True
                }
            }

            await self.premium_col.insert_one(trial_data)
            return True, expires_at

        except Exception as e:
            return False, str(e)

    async def can_use_3day_trial(self, user_id):
        """Check if user can activate 3-day trial"""
        return await self.can_use_trial(user_id)

    async def get_trial_status(self, user_id):
        """Get user's trial status - whether they have used their free trial"""
        monthly_usage = await self.get_monthly_usage(user_id)
        return {
            'used': monthly_usage.get('trial_activated', False),
            'trial_processes': monthly_usage.get('trial_processes', 0),
            'granted_at': monthly_usage.get('trial_granted_at')
        }

    async def get_user_process_limit(self, user_id):
        """Get user's total process limit including trials"""
        base_limit = await self.get_forwarding_limit(user_id)
        if base_limit == -1:  # Premium user
            return -1

        # Check for trial processes
        monthly_usage = await self.get_monthly_usage(user_id)
        trial_processes = monthly_usage.get('trial_processes', 0)
        return base_limit + trial_processes

    async def get_all_premium_users(self):
        """Get all premium users"""
        return await self.premium_col.find({'is_active': True}).to_list(length=1000)

    async def cleanup_expired_premium(self):
        """Remove expired premium subscriptions"""
        result = await self.premium_col.update_many(
            {'expires_at': {'$lt': datetime.utcnow()}},
            {'$set': {'is_active': False}}
        )
        return result.modified_count

    # Payment verification system
    async def submit_payment_verification(self, user_id, screenshot_file_id, plan_type='pro', duration_days=30, amount=None):
        """Submit payment verification with plan support"""
        verification_data = {
            'user_id': int(user_id),
            'screenshot_file_id': screenshot_file_id,
            'plan_type': plan_type,
            'duration_days': duration_days,
            'amount': amount,
            'payment_method': '6354228145@axl',
            'submitted_at': datetime.utcnow(),
            'status': 'pending',  # pending, approved, rejected
            'reviewed_by': None,
            'reviewed_at': None,
            'review_notes': None
        }
        result = await self.payment_col.insert_one(verification_data)
        return result.inserted_id

    async def get_pending_verifications(self):
        """Get all pending payment verifications"""
        return await self.payment_col.find({'status': 'pending'}).to_list(length=100)

    async def approve_payment(self, verification_id, admin_id, notes=None):
        """Approve payment verification"""
        result = await self.payment_col.update_one(
            {'_id': verification_id},
            {
                '$set': {
                    'status': 'approved',
                    'reviewed_by': int(admin_id),
                    'reviewed_at': datetime.utcnow(),
                    'review_notes': notes
                }
            }
        )

        # Get the verification to add premium subscription
        verification = await self.payment_col.find_one({'_id': verification_id})
        if verification and result.modified_count > 0:
            # Add premium subscription based on plan and duration
            await self.add_premium_user(
                verification['user_id'], 
                verification.get('plan_type', 'pro'),
                verification.get('duration_days', 30),
                verification.get('amount')
            )

        return result.modified_count > 0

    async def reject_payment(self, verification_id, admin_id, notes=None):
        """Reject payment verification"""
        result = await self.payment_col.update_one(
            {'_id': verification_id},
            {
                '$set': {
                    'status': 'rejected',
                    'reviewed_by': int(admin_id),
                    'reviewed_at': datetime.utcnow(),
                    'review_notes': notes or 'Payment verification rejected'
                }
            }
        )
        return result.modified_count > 0

    async def get_verification_by_id(self, verification_id):
        """Get verification details by ID"""
        return await self.payment_col.find_one({'_id': verification_id})

    # Usage tracking for daily limits
    async def get_daily_usage(self, user_id):
        """Get user's usage for current day"""
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        usage = await self.usage_col.find_one({
            'user_id': int(user_id),
            'date': start_of_day
        })
        return usage if usage else {'user_id': int(user_id), 'date': start_of_day, 'processes': 0}

    async def increment_usage(self, user_id):
        """Increment user's monthly usage"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        await self.usage_col.update_one(
            {'user_id': int(user_id), 'date': start_of_month},
            {
                '$inc': {'processes': 1},
                '$set': {'last_used': datetime.utcnow()}
            },
            upsert=True
        )

    async def can_user_process(self, user_id):
        """Check if user can process based on their plan (including trial processes)"""
        # Get user's total forwarding limit (including trial processes)
        limit = await self.get_user_process_limit(user_id)

        # Unlimited for premium plans (Plus and Pro)
        if limit == -1:
            return True, "unlimited"

        # Check monthly usage for free users
        usage = await self.get_monthly_usage(user_id)
        if usage['processes'] >= limit:
            return False, "monthly_limit_reached"

        return True, "allowed"

    # Force subscribe functionality
    async def is_user_subscribed_to_channel(self, user_id, channel_id, client):
        """
        Check if user is subscribed to a specific channel
        
        Args:
            user_id (int): User ID to check
            channel_id (int): Channel ID to check
            client: Pyrogram client instance
            
        Returns:
            bool: True if subscribed, False otherwise
        """
        try:
            # Convert string channel_id to int if needed
            if isinstance(channel_id, str):
                if channel_id.startswith('-'):
                    channel_id = int(channel_id)
                else:
                    # Skip invalid channel IDs
                    logger.warning(f"Skipping invalid channel ID format: {channel_id}")
                    return False
                    
            member = await client.get_chat_member(channel_id, user_id)
            return member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]
        except Exception as e:
            # Don't log USERNAME_INVALID errors as they're expected for some channels
            if "USERNAME_INVALID" not in str(e):
                logger.error(f"Error checking channel {channel_id}: {e}")
            return False

    async def check_force_subscribe(self, user_id, client):
        """Check if user is subscribed to all required channels"""
        from config import Config

        try:
            if not Config.MULTI_FSUB:
                return {'all_subscribed': True, 'missing_channels': []}

            all_subscribed = True
            missing_channels = []

            for channel_id in Config.MULTI_FSUB:
                try:
                    # Convert to int if string
                    if isinstance(channel_id, str):
                        if channel_id.strip().lstrip('-').isdigit():
                            channel_id = int(channel_id)
                        else:
                            logger.warning(f"Skipping invalid channel ID: {channel_id}")
                            continue
                            
                    member = await client.get_chat_member(channel_id, user_id)
                    subscribed = member.status not in ['left', 'kicked']
                    
                    if not subscribed:
                        all_subscribed = False
                        try:
                            chat = await client.get_chat(channel_id)
                            missing_channels.append(chat.title or f"Channel {abs(channel_id)}")
                        except:
                            missing_channels.append(f"Channel {abs(channel_id)}")
                            
                except Exception as e:
                    # Skip channels that cause USERNAME_INVALID or other errors
                    if "USERNAME_INVALID" not in str(e):
                        logger.error(f"Error checking channel {channel_id}: {e}")
                    all_subscribed = False
                    missing_channels.append(f"Channel {abs(int(channel_id)) if str(channel_id).lstrip('-').isdigit() else channel_id}")

                    if not subscribed:
                        all_subscribed = False
                        missing_channels.append(f"Channel {channel_id}")

                except Exception as e:
                    print(f"Error checking channel {channel_id}: {e}")
                    all_subscribed = False
                    missing_channels.append(f"Channel {channel_id}")

            result = {
                'all_subscribed': all_subscribed,
                'missing_channels': missing_channels
            }

            print(f"Subscription check result for user {user_id}: {result}")
            return result

        except Exception as e:
            print(f"Force subscribe check error: {e}")
            return {
                'all_subscribed': False,
                'missing_channels': ['Required channels']
            }

    # Admin chat sessions
    async def start_admin_chat(self, admin_id, target_user_id):
        """Start admin chat session with user"""
        chat_data = {
            'admin_id': int(admin_id),
            'target_user_id': int(target_user_id),
            'started_at': datetime.utcnow(),
            'is_active': True,
            'messages': []
        }

        # End any existing chat session for this admin
        await self.admin_chat_col.update_many(
            {'admin_id': int(admin_id), 'is_active': True},
            {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
        )

        result = await self.admin_chat_col.insert_one(chat_data)
        return result.inserted_id

    async def get_active_admin_chat(self, admin_id):
        """Get active admin chat session"""
        return await self.admin_chat_col.find_one({
            'admin_id': int(admin_id),
            'is_active': True
        })

    async def end_admin_chat(self, admin_id):
        """End admin chat session"""
        return await self.admin_chat_col.update_many(
            {'admin_id': int(admin_id), 'is_active': True},
            {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
        )

    async def add_chat_message(self, session_id, from_admin, message_text):
        """Add message to admin chat session"""
        message_data = {
            'from_admin': from_admin,
            'message': message_text,
            'timestamp': datetime.utcnow()
        }
        return await self.admin_chat_col.update_one(
            {'_id': session_id},
            {'$push': {'messages': message_data}}
        )

    async def get_active_chat_for_user(self, user_id):
        """Get active admin chat session for a specific user"""
        return await self.admin_chat_col.find_one({
            'target_user_id': int(user_id),
            'is_active': True
        })

    async def get_active_admin_chat(self, admin_id):
        """Get active admin chat session for a specific admin"""
        return await self.admin_chat_col.find_one({
            'admin_id': int(admin_id),
            'is_active': True
        })

    # Contact requests methods
    async def create_contact_request(self, user_id):
        """Create a new contact request"""
        contact_data = {
            'user_id': int(user_id),
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'reviewed_at': None,
            'reviewed_by': None
        }

        result = await self.contact_requests_col.insert_one(contact_data)
        return result.inserted_id

    async def create_chat_request(self, user_id):
        """Create a new chat request"""
        chat_data = {
            'user_id': int(user_id),
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=24),  # Auto-expire after 24 hours
            'reviewed_at': None,
            'reviewed_by': None,
            'notifications': []  # Store notification message IDs for cleanup
        }

        result = await self.chat_requests_col.insert_one(chat_data)
        return result.inserted_id

    async def get_pending_chat_request(self, user_id):
        """Get pending chat request for user"""
        return await self.chat_requests_col.find_one({
            'user_id': int(user_id),
            'status': 'pending'
        })

    async def get_chat_request_by_id(self, request_id):
        """Get chat request by ID"""
        return await self.chat_requests_col.find_one({
            '_id': ObjectId(request_id)
        })

    async def update_chat_request_status(self, request_id, status, admin_id=None):
        """Update chat request status"""
        update_data = {
            'status': status,
            'reviewed_at': datetime.utcnow()
        }
        if admin_id:
            update_data['reviewed_by'] = int(admin_id)

        return await self.chat_requests_col.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': update_data}
        )

    async def store_chat_notifications(self, request_id, notification_messages):
        """Store notification message IDs for cleanup"""
        return await self.chat_requests_col.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {'notifications': notification_messages}}
        )

    async def cleanup_chat_notifications(self, request_id, client, accepting_admin_id):
        """Delete notifications from all other admins when one admin accepts"""
        try:
            # Get the request to find notification messages
            request = await self.get_chat_request_by_id(request_id)
            if not request or 'notifications' not in request:
                return

            # Delete messages from all admins except the one who accepted
            for notification in request['notifications']:
                if notification['admin_id'] != accepting_admin_id:
                    try:
                        await client.delete_messages(
                            chat_id=notification['admin_id'],
                            message_ids=notification['message_id']
                        )
                    except Exception as e:
                        print(f"Failed to delete notification for admin {notification['admin_id']}: {e}")
        except Exception as e:
            print(f"Error cleaning up notifications: {e}")

    async def cleanup_expired_chat_requests(self):
        """Remove chat requests and data older than 24 hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Find expired requests
        expired_requests = self.chat_requests_col.find({
            'created_at': {'$lt': cutoff_time}
        })

        # Also cleanup any active chat sessions from expired requests
        async for request in expired_requests:
            if request.get('status') == 'accepted':
                # End any active chat sessions
                await self.admin_chat_col.update_many(
                    {'target_user_id': request['user_id'], 'is_active': True},
                    {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
                )

        # Delete expired chat requests
        result = await self.chat_requests_col.delete_many({
            'created_at': {'$lt': cutoff_time}
        })

        return result.deleted_count

    async def get_pending_contact_request(self, user_id):
        """Get pending contact request for user"""
        return await self.contact_requests_col.find_one({
            'user_id': int(user_id),
            'status': 'pending'
        })

    async def get_contact_request_by_id(self, request_id):
        """Get contact request by ID"""
        return await self.contact_requests_col.find_one({
            '_id': ObjectId(request_id)
        })

    async def update_contact_request_status(self, request_id, status):
        """Update contact request status"""
        return await self.contact_requests_col.update_one(
            {'_id': ObjectId(request_id)},
            {
                '$set': {
                    'status': status,
                    'reviewed_at': datetime.utcnow()
                }
            }
        )

    # ===============================
    # REFERRAL SYSTEM METHODS
    # ===============================

    def _generate_referral_code(self, user_id):
        """Generate unique referral code: ftmbotzx + 4 random chars = 12 total"""
        import random
        import string
        
        # Generate 4 random alphanumeric characters (ftmbotzx = 8 chars + 4 = 12 total)
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        code = f"ftmbotzx{random_chars}"
        logger.info(f"Generated referral code {code} for user {user_id}")
        return code

    async def create_referral_code(self, user_id):
        """Create and assign referral code to user"""
        try:
            # Check if user already has referral code
            user = await self.get_user(user_id)
            if user and user.get('referral_code'):
                logger.info(f"User {user_id} already has referral code: {user['referral_code']}")
                return user['referral_code']
            
            # Generate unique referral code
            max_attempts = 10
            for attempt in range(max_attempts):
                referral_code = self._generate_referral_code(user_id)
                
                # Check if code already exists
                existing_user = await self.col.find_one({'referral_code': referral_code})
                if not existing_user:
                    # Assign code to user
                    result = await self.col.update_one(
                        {'id': int(user_id)},
                        {'$set': {'referral_code': referral_code}},
                        upsert=True
                    )
                    
                    if result.matched_count > 0 or result.upserted_id:
                        logger.info(f"Assigned referral code {referral_code} to user {user_id}")
                        return referral_code
                    else:
                        logger.warning(f"Failed to assign referral code on attempt {attempt + 1}")
            
            # Fallback: use user_id in code if all random attempts fail
            referral_code = f"ftmbotzx{str(user_id)[-4:].zfill(4)}"
            await self.col.update_one(
                {'id': int(user_id)},
                {'$set': {'referral_code': referral_code}},
                upsert=True
            )
            logger.info(f"Assigned fallback referral code {referral_code} to user {user_id}")
            return referral_code
            
        except Exception as e:
            logger.error(f"Error creating referral code for user {user_id}: {e}")
            # Emergency fallback
            fallback_code = f"ftmbotzx{str(user_id)[-4:].zfill(4)}"
            return fallback_code

    async def get_referral_code(self, user_id):
        """Get user's referral code, create if doesn't exist"""
        user = await self.get_user(user_id)
        if user and user.get('referral_code'):
            return user['referral_code']
        
        # Create new referral code
        return await self.create_referral_code(user_id)

    async def get_user_by_referral_code(self, referral_code):
        """Get user by their referral code"""
        try:
            user = await self.col.find_one({'referral_code': referral_code})
            logger.info(f"Looking for user with referral code {referral_code}: {'Found' if user else 'Not found'}")
            return user
        except Exception as e:
            logger.error(f"Error getting user by referral code {referral_code}: {e}")
            return None

    async def set_user_referred_by(self, user_id, referral_code):
        """Set who referred this user"""
        try:
            logger.info(f"Setting referral for user {user_id} with code {referral_code}")
            
            # First ensure the user has a referral code created if they don't have one
            await self.create_referral_code(user_id)
            
            # Find the referring user
            referring_user = await self.get_user_by_referral_code(referral_code)
            if not referring_user:
                logger.error(f"No user found with referral code: {referral_code}")
                return False
            
            referring_user_id = referring_user['id']
            logger.info(f"Found referring user: {referring_user_id}")
            
            # Don't allow self-referral
            if int(referring_user_id) == int(user_id):
                logger.warning(f"Self-referral attempt blocked for user {user_id}")
                return False
            
            # Check if this user already has any referral record
            existing_user_data = await self.get_user(user_id)
            if existing_user_data and existing_user_data.get('referred_by'):
                logger.warning(f"User {user_id} already has a referrer: {existing_user_data.get('referred_by')}")
                return False
            
            # Check if referral tracking record already exists
            existing_referral = await self.referral_col.find_one({
                'referred_user_id': int(user_id)
            })
            
            if existing_referral:
                logger.warning(f"User {user_id} already has a referral tracking record")
                return False
            
            # Update the referred user in the users collection
            update_result = await self.col.update_one(
                {'id': int(user_id)},
                {'$set': {
                    'referred_by': int(referring_user_id),
                    'referral_completed': False
                }},
                upsert=True
            )
            
            logger.info(f"✅ Updated user {user_id} referred_by field to {referring_user_id}")
            
            # Create referral tracking record
            referral_data = {
                'referrer_user_id': int(referring_user_id),
                'referred_user_id': int(user_id),
                'referral_code': referral_code,
                'created_at': datetime.utcnow(),
                'completed': False,
                'completed_at': None,
                'bot_started': False,
                'channels_joined': False,
                'tracking_notification_sent': False,
                'completion_notification_sent': False
            }
            
            try:
                insert_result = await self.referral_col.insert_one(referral_data)
                if insert_result.inserted_id:
                    logger.info(f"✅ Created referral tracking record: {insert_result.inserted_id} for referrer {referring_user_id} -> referred {user_id}")
                    return True
                else:
                    logger.error(f"Failed to create referral tracking record")
                    return False
            except Exception as insert_error:
                logger.error(f"Error inserting referral tracking record: {insert_error}")
                return False
            
        except Exception as e:
            logger.error(f"Error in set_user_referred_by for user {user_id} with code {referral_code}: {e}", exc_info=True)
            return False

    async def mark_referral_bot_started(self, user_id):
        """Mark that referred user has started the bot"""
        result = await self.referral_col.update_one(
            {'referred_user_id': int(user_id), 'completed': False},
            {'$set': {'bot_started': True}}
        )
        
        logger.info(f"Marked bot started for referred user {user_id}: {result.modified_count} record(s) updated")
        
        # Check if referral should be completed
        if result.modified_count > 0:
            await self._check_and_complete_referral(user_id)

    async def mark_referral_channels_joined(self, user_id):
        """Mark that referred user has joined all required channels"""
        result = await self.referral_col.update_one(
            {'referred_user_id': int(user_id), 'completed': False},
            {'$set': {'channels_joined': True}}
        )
        
        # Check if referral should be completed
        if result.modified_count > 0:
            return await self._check_and_complete_referral(user_id)
        return False

    async def _check_and_complete_referral(self, user_id):
        """Check if referral is complete and mark it as such with auto-rewards"""
        referral = await self.referral_col.find_one({
            'referred_user_id': int(user_id),
            'completed': False,
            'bot_started': True,
            'channels_joined': True
        })
        
        if referral:
            logger.info(f"Completing referral for user {user_id} (referrer: {referral['referrer_user_id']})")
            
            # Complete the referral
            await self.referral_col.update_one(
                {'_id': referral['_id']},
                {'$set': {
                    'completed': True,
                    'completed_at': datetime.utcnow(),
                    'completion_notification_sent': True
                }}
            )
            
            # Update user record
            await self.col.update_one(
                {'id': int(user_id)},
                {'$set': {'referral_completed': True}}
            )
            
            # Auto-grant 1 day Plus plan to referred user
            await self.add_premium_user(
                user_id,
                plan_type="plus",
                duration_days=1,
                amount_paid="referral_welcome_bonus"
            )
            logger.info(f"Granted 1-day Plus plan to referred user {user_id}")
            
            # Check if referrer should get milestone rewards
            reward_granted, total_referrals = await self._check_auto_upgrade(referral['referrer_user_id'])
            
            return {
                'completed': True,
                'referrer_user_id': referral['referrer_user_id'],
                'referred_user_id': user_id,
                'reward_granted': reward_granted,
                'total_referrals': total_referrals
            }
        
        logger.warning(f"No valid referral found for user {user_id} to complete")
        return False

    async def _check_auto_upgrade(self, referrer_user_id):
        """Check if user should get auto-upgraded for reaching milestones"""
        # Count completed referrals
        completed_count = await self.referral_col.count_documents({
            'referrer_user_id': int(referrer_user_id),
            'completed': True
        })
        
        # Check if user should get upgrade
        reward_granted = False
        
        # 15 referrals = Plus plan (30 days)
        if completed_count == 15:
            # Check if user already has this reward
            existing_reward = await self.premium_col.find_one({
                'user_id': int(referrer_user_id),
                'referral_milestone': 15
            })
            
            if not existing_reward:
                # Auto-upgrade to Plus plan for 30 days
                result = await self.premium_col.insert_one({
                    'user_id': int(referrer_user_id),
                    'plan_type': 'plus',
                    'duration_days': 30,
                    'amount_paid': 'referral_15_milestone',
                    'subscribed_at': datetime.utcnow(),
                    'expires_at': datetime.utcnow() + timedelta(days=30),
                    'is_active': True,
                    'auto_renew': False,
                    'referral_milestone': 15,
                    'features': self._get_plan_features('plus')
                })
                reward_granted = True
                logger.info(f"Auto-granted Plus 30d to user {referrer_user_id} for 15 referrals")
        
        # 30 referrals = Pro plan (15 days)
        elif completed_count == 30:
            # Check if user already has this reward
            existing_reward = await self.premium_col.find_one({
                'user_id': int(referrer_user_id),
                'referral_milestone': 30
            })
            
            if not existing_reward:
                # Auto-upgrade to Pro plan for 15 days
                result = await self.premium_col.insert_one({
                    'user_id': int(referrer_user_id),
                    'plan_type': 'pro',
                    'duration_days': 15,
                    'amount_paid': 'referral_30_milestone',
                    'subscribed_at': datetime.utcnow(),
                    'expires_at': datetime.utcnow() + timedelta(days=15),
                    'is_active': True,
                    'auto_renew': False,
                    'referral_milestone': 30,
                    'features': self._get_plan_features('pro')
                })
                reward_granted = True
                logger.info(f"Auto-granted Pro 15d to user {referrer_user_id} for 30 referrals")
        
        return reward_granted, completed_count

    async def get_referral_stats(self, user_id):
        """Get comprehensive referral statistics for user"""
        # Get completed referrals
        completed_referrals = await self.referral_col.find({
            'referrer_user_id': int(user_id),
            'completed': True
        }).to_list(length=100)
        
        # Get pending referrals (started but not completed)
        pending_referrals = await self.referral_col.find({
            'referrer_user_id': int(user_id),
            'completed': False
        }).to_list(length=100)
        
        # Get user's referral code
        user_code = await self.get_referral_code(user_id)
        
        # Calculate stats
        total_completed = len(completed_referrals)
        total_pending = len(pending_referrals)
        remaining_for_reward = max(0, 15 - total_completed)
        
        # Check if already got reward
        has_received_reward = total_completed >= 15
        
        return {
            'referral_code': user_code,
            'total_completed': total_completed,
            'total_pending': total_pending,
            'remaining_for_reward': remaining_for_reward,
            'has_received_reward': has_received_reward,
            'completed_referrals': completed_referrals,
            'pending_referrals': pending_referrals
        }

    async def get_referral_leaderboard(self, limit=10):
        """Get top referrers leaderboard"""
        pipeline = [
            {
                '$match': {'completed': True}
            },
            {
                '$group': {
                    '_id': '$referrer_user_id',
                    'total_referrals': {'$sum': 1}
                }
            },
            {
                '$sort': {'total_referrals': -1}
            },
            {
                '$limit': limit
            }
        ]
        
        return await self.referral_col.aggregate(pipeline).to_list(length=limit)

    async def is_referral_completed(self, user_id):
        """Check if user's referral is completed"""
        user = await self.get_user(user_id)
        return user.get('referral_completed', False) if user else False
    
    async def has_incomplete_referral(self, user_id):
        """Check if user has an incomplete referral that needs completion"""
        # Check user record
        user = await self.get_user(user_id)
        if not user or not user.get('referred_by') or user.get('referral_completed'):
            return False
        
        # Check referral tracking record
        referral = await self.referral_col.find_one({
            'referred_user_id': int(user_id),
            'completed': False
        })
        
        return referral is not None

    async def get_referrer_of_user(self, user_id):
        """Get who referred this user"""
        user = await self.get_user(user_id)
        if user and user.get('referred_by'):
            return await self.get_user(user['referred_by'])
        return None

    async def get_all_referrals(self, user_id):
        """Get all referrals made by a specific user"""
        referrals = await self.referral_col.find({
            'referrer_user_id': int(user_id)
        }).to_list(length=100)
        return referrals

db = Database(Config.DATABASE_URI, Config.DATABASE_NAME)