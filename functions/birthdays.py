"""
functions/birthdays.py
Birthday tracking and celebration system.
"""

import logging
from datetime import datetime, date
from typing import Optional, List
import config

logger = logging.getLogger("miso.functions.birthdays")


async def set_birthday(guild_id: int, user_id: int, month: int, day: int, year: int = None) -> dict:
    """
    Set a user's birthday.
    
    Returns:
        dict with keys: success, message
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'Birthdays not available'}
    
    # Validate date
    try:
        if month < 1 or month > 12:
            return {'success': False, 'message': 'Month must be between 1 and 12!'}
        if day < 1 or day > 31:
            return {'success': False, 'message': 'Day must be between 1 and 31!'}
        if year and (year < 1900 or year > datetime.now().year):
            return {'success': False, 'message': 'Invalid year!'}
        
        # Validate actual date exists
        test_year = year if year else 2000
        date(test_year, month, day)
    except ValueError:
        return {'success': False, 'message': 'Invalid date!'}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        data = {
            'guild_id': str(guild_id),
            'user_id': str(user_id),
            'birth_month': month,
            'birth_day': day,
            'birth_year': year
        }
        
        supabase.table('user_birthdays').upsert(data, on_conflict='guild_id,user_id').execute()
        
        logger.info(f"Set birthday for user {user_id} in guild {guild_id}: {month}/{day}/{year if year else 'XXXX'}")
        return {'success': True, 'message': 'Birthday set successfully!'}
        
    except Exception as e:
        logger.error(f"Failed to set birthday: {e}", exc_info=True)
        return {'success': False, 'message': f'Error: {str(e)}'}


async def get_birthday(guild_id: int, user_id: int) -> Optional[dict]:
    """
    Get a user's birthday.
    
    Returns:
        dict with month, day, year (optional), last_celebrated
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('user_birthdays').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get birthday: {e}")
        return None


async def delete_birthday(guild_id: int, user_id: int) -> bool:
    """Delete a user's birthday."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        supabase.table('user_birthdays').delete().eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        logger.info(f"Deleted birthday for user {user_id} in guild {guild_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete birthday: {e}")
        return False


async def get_todays_birthdays(guild_id: int) -> List[dict]:
    """
    Get all birthdays happening today in a guild.
    
    Returns:
        List of birthday records
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        today = datetime.now()
        
        response = supabase.table('user_birthdays').select('*').eq('guild_id', str(guild_id)).eq('birth_month', today.month).eq('birth_day', today.day).execute()
        
        if response.data:
            # Filter out those already celebrated today
            today_str = today.date().isoformat()
            return [bd for bd in response.data if bd.get('last_celebrated') != today_str]
        return []
    except Exception as e:
        logger.error(f"Failed to get today's birthdays: {e}")
        return []


async def mark_birthday_celebrated(guild_id: int, user_id: int) -> bool:
    """Mark a birthday as celebrated for today."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        today_str = datetime.now().date().isoformat()
        
        supabase.table('user_birthdays').update({
            'last_celebrated': today_str
        }).eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        return True
    except Exception as e:
        logger.error(f"Failed to mark birthday celebrated: {e}")
        return False


async def get_birthday_settings(guild_id: int) -> dict:
    """Get birthday celebration settings for a guild."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {
            'enabled': False,
            'announcement_channel_id': None,
            'message_template': '🎉 Happy Birthday {user}! 🎂',
            'bonus_xp': 500,
            'bonus_coins': 1000
        }
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('birthday_settings').select('*').eq('guild_id', str(guild_id)).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return {
            'enabled': False,
            'announcement_channel_id': None,
            'message_template': '🎉 Happy Birthday {user}! 🎂',
            'bonus_xp': 500,
            'bonus_coins': 1000
        }
    except Exception as e:
        logger.error(f"Failed to get birthday settings: {e}")
        return {
            'enabled': False,
            'announcement_channel_id': None,
            'message_template': '🎉 Happy Birthday {user}! 🎂',
            'bonus_xp': 500,
            'bonus_coins': 1000
        }


async def save_birthday_settings(guild_id: int, settings: dict) -> bool:
    """Save birthday celebration settings."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        data = {
            'guild_id': str(guild_id),
            'enabled': settings.get('enabled', False),
            'announcement_channel_id': str(settings['announcement_channel_id']) if settings.get('announcement_channel_id') else None,
            'message_template': settings.get('message_template', '🎉 Happy Birthday {user}! 🎂'),
            'bonus_xp': settings.get('bonus_xp', 500),
            'bonus_coins': settings.get('bonus_coins', 1000)
        }
        
        supabase.table('birthday_settings').upsert(data, on_conflict='guild_id').execute()
        return True
    except Exception as e:
        logger.error(f"Failed to save birthday settings: {e}")
        return False
