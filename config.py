from os import environ 
import sys

class Config:
    # Required environment variables - no defaults for security
    API_ID = environ.get("API_ID")
    API_HASH = environ.get("API_HASH")
    BOT_TOKEN = environ.get("BOT_TOKEN")
    DATABASE_URI = environ.get("DATABASE")
    OWNER_ID_STR = environ.get("OWNER_ID")
    
    # Validate required environment variables
    @classmethod
    def validate_env(cls):
        """Validate that all required environment variables are set"""
        required_vars = ['API_ID', 'API_HASH', 'BOT_TOKEN', 'DATABASE', 'OWNER_ID']
        missing_vars = []
        
        for var in required_vars:
            if not environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("Please set these environment variables before running the bot.")
            sys.exit(1)
    
    # Initialize configuration after validation
    BOT_SESSION = environ.get("BOT_SESSION", "forward-bot") 
    DATABASE_NAME = environ.get("DATABASE_NAME", "forward-dbs")
    OWNER_ID = [int(id) for id in OWNER_ID_STR.split()] if OWNER_ID_STR else []
    ADMIN_ID = [int(id) for id in environ.get("ADMIN_ID", "7810783444").split() if id.strip()] if environ.get("ADMIN_ID") else []
    LOG_CHANNEL_ID = int(environ.get("LOG_CHANNEL_ID", "0")) if environ.get("LOG_CHANNEL_ID") else None
    SUPPORT_GROUP = "https://t.me/ftmbotzx_support"
    UPDATE_CHANNEL = "https://t.me/ftmbotzx"
    # Multi Force Subscribe - space separated channel IDs
    MULTI_FSUB_STR = environ.get("MULTI_FSUB", "-1002282331890 -1002087228619")
    MULTI_FSUB = MULTI_FSUB_STR.split() if MULTI_FSUB_STR else []
    MULTI_FSUB = [int(x) for x in MULTI_FSUB if x.strip().lstrip('-').isdigit()]
    
    # UPI ID for payments
    UPI_ID = environ.get("UPI_ID", "ftmdeveloperz@ybl")
    CHANNEL_ID=MULTI_FSUB_STR
    # Three-tier pricing structure
    PLAN_PRICING = {
        'plus': {
            '15_days': 199,
            '30_days': 299
        },
        'pro': {
            '15_days': 299,
            '30_days': 549
        }
    }
    
    # Plan features
    PLAN_FEATURES = {
        'free': {
            'forwarding_limit': 1,  # per month
            'ftm_mode': False,
            'priority_support': False,
            'unlimited_forwarding': False
        },
        'plus': {
            'forwarding_limit': -1,  # unlimited
            'ftm_mode': False,
            'priority_support': False,
            'unlimited_forwarding': True
        },
        'pro': {
            'forwarding_limit': -1,  # unlimited
            'ftm_mode': True,  # FTM Delta mode
            'priority_support': True,
            'unlimited_forwarding': True
        }
    }
    
    @staticmethod
    def is_sudo_user(user_id):
        """Check if user is sudo (owner or admin)"""
        return int(user_id) in Config.OWNER_ID or int(user_id) in Config.ADMIN_ID

class temp(object): 
    lock = {}
    CANCEL = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []
    CURRENT_PROCESSES = {}  # Track ongoing processes per user
    
