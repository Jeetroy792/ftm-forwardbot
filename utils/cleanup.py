import asyncio
import logging
from datetime import datetime, timedelta
from database import db

async def periodic_cleanup():
    """
    Periodic cleanup task that runs every hour to clean up expired chat requests
    and data older than 24 hours
    """
    logger = logging.getLogger(__name__)
    
    while True:
        try:
            # Clean up expired chat requests (older than 24 hours)
            deleted_count = await db.cleanup_expired_chat_requests()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired chat requests")
                
            # Sleep for 1 hour before next cleanup
            await asyncio.sleep(3600)  # 3600 seconds = 1 hour
            
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            # Sleep for 5 minutes before retrying
            await asyncio.sleep(300)

async def manual_cleanup():
    """
    Manual cleanup function that can be called on demand
    """
    try:
        deleted_count = await db.cleanup_expired_chat_requests()
        return deleted_count
    except Exception as e:
        logging.error(f"Error in manual cleanup: {e}")
        return 0