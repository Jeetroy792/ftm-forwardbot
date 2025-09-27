"""
Timezone conversion utility module
Converts all UTC times to IST (Indian Standard Time)
IST = UTC + 5:30
"""

from datetime import datetime, timedelta, timezone
from typing import Union, Optional

# Define IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def utc_to_ist(utc_time: Union[datetime, str, None]) -> Optional[datetime]:
    """
    Convert UTC datetime to IST datetime
    
    Args:
        utc_time: UTC datetime object, ISO string, or None
        
    Returns:
        datetime object in IST timezone or None if input is None
    """
    if utc_time is None:
        return None
    
    # Handle string input (ISO format)
    if isinstance(utc_time, str):
        try:
            utc_time = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
        except ValueError:
            # Try parsing without timezone info (assume UTC)
            utc_time = datetime.fromisoformat(utc_time)
    
    # If datetime is naive (no timezone), assume it's UTC
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=timezone.utc)
    
    # Convert to IST
    ist_time = utc_time.astimezone(IST)
    return ist_time

def now_ist() -> datetime:
    """
    Get current time in IST timezone
    
    Returns:
        Current datetime in IST
    """
    return datetime.now(IST)

def utc_now_to_ist() -> datetime:
    """
    Get current UTC time converted to IST
    
    Returns:
        Current UTC time converted to IST
    """
    return datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(IST)

def format_ist_time(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S IST") -> str:
    """
    Format IST datetime to string
    
    Args:
        dt: datetime object in IST
        format_str: Format string for output
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return "N/A"
    
    # Ensure the datetime is in IST
    if dt.tzinfo != IST:
        dt = utc_to_ist(dt)
        if dt is None:
            return "N/A"
    
    return dt.strftime(format_str)

def get_time_difference_ist(start_time: datetime, end_time: Optional[datetime] = None) -> str:
    """
    Get human-readable time difference in IST
    
    Args:
        start_time: Start time (will be converted to IST)
        end_time: End time (defaults to current IST time)
        
    Returns:
        Human-readable time difference string
    """
    # Convert start time to IST
    start_ist = utc_to_ist(start_time)
    if start_ist is None:
        return "N/A"
    
    # Use current IST time if end_time not provided
    if end_time is None:
        end_ist = now_ist()
    else:
        end_ist = utc_to_ist(end_time)
        if end_ist is None:
            return "N/A"
    
    diff = end_ist - start_ist
    
    # Calculate human-readable difference
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "Just now"

def ist_to_utc(ist_time: datetime) -> datetime:
    """
    Convert IST datetime back to UTC (if needed)
    
    Args:
        ist_time: datetime object in IST
        
    Returns:
        datetime object in UTC
    """
    if ist_time.tzinfo != IST:
        # Assume it's IST if no timezone
        ist_time = ist_time.replace(tzinfo=IST)
    
    return ist_time.astimezone(timezone.utc)

# Convenience functions for common use cases
def display_joined_date(joined_date_utc: Optional[datetime]) -> str:
    """Display user joined date in IST"""
    if joined_date_utc is None:
        return "N/A"
    ist_date = utc_to_ist(joined_date_utc)
    return format_ist_time(ist_date, "%d %B %Y at %H:%M IST") if ist_date else "N/A"

def display_subscription_date(sub_date_utc: Optional[datetime]) -> str:
    """Display subscription date in IST"""
    if sub_date_utc is None:
        return "N/A"
    ist_date = utc_to_ist(sub_date_utc)
    return format_ist_time(ist_date, "%d %B %Y at %H:%M IST") if ist_date else "N/A"

def display_expiry_date(expiry_date_utc: Optional[datetime]) -> str:
    """Display expiry date in IST"""
    if expiry_date_utc is None:
        return "N/A"
    ist_date = utc_to_ist(expiry_date_utc)
    return format_ist_time(ist_date, "%d %B %Y at %H:%M IST") if ist_date else "N/A"

def time_until_expiry(expiry_date_utc: Optional[datetime]) -> str:
    """Get time remaining until expiry in human-readable format"""
    if expiry_date_utc is None:
        return "N/A"
    
    expiry_ist = utc_to_ist(expiry_date_utc)
    if expiry_ist is None:
        return "N/A"
    
    current_ist = now_ist()
    
    if expiry_ist <= current_ist:
        return "Expired"
    
    diff = expiry_ist - current_ist
    
    if diff.days > 0:
        return f"{diff.days} days remaining"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours remaining"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes remaining"
    else:
        return "Expiring soon"

def get_current_ist_timestamp() -> str:
    """Get current timestamp in IST for logging"""
    return now_ist().strftime("%Y-%m-%d %H:%M:%S IST")