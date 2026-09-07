"""
functions/level_up_messages.py
Custom level-up message settings per guild.
"""

import logging
from typing import Optional
import config

logger = logging.getLogger("miso.functions.level_up_messages")


async def get_level_up_settings(guild_id: int) -> dict:
    """
    Get level-up message settings for a guild.
    
    Returns:
        dict with keys: enabled, channel_id, message_template, embed_color, send_dm
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {
            'enabled': True,
            'channel_id': None,  # None = same channel
            'message_template': 'Congratulations {user}! You\'ve reached **Level {level}**!',
            'embed_color': 16766720,  # Gold
            'send_dm': False
        }
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('level_up_settings').select('*').eq('guild_id', str(guild_id)).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        # Return defaults
        return {
            'enabled': True,
            'channel_id': None,
            'message_template': 'Congratulations {user}! You\'ve reached **Level {level}**!',
            'embed_color': 16766720,
            'send_dm': False
        }
    except Exception as e:
        logger.error(f"Failed to fetch level-up settings: {e}")
        return {
            'enabled': True,
            'channel_id': None,
            'message_template': 'Congratulations {user}! You\'ve reached **Level {level}**!',
            'embed_color': 16766720,
            'send_dm': False
        }


async def save_level_up_settings(guild_id: int, settings: dict) -> bool:
    """
    Save level-up message settings for a guild.
    
    Args:
        guild_id: Guild ID
        settings: Dict with keys enabled, channel_id, message_template, embed_color, send_dm
    
    Returns:
        True if successful
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        data = {
            'guild_id': str(guild_id),
            'enabled': settings.get('enabled', True),
            'channel_id': str(settings['channel_id']) if settings.get('channel_id') else None,
            'message_template': settings.get('message_template', 'Congratulations {user}! You\'ve reached **Level {level}**!'),
            'embed_color': settings.get('embed_color', 16766720),
            'send_dm': settings.get('send_dm', False)
        }
        
        supabase.table('level_up_settings').upsert(data, on_conflict='guild_id').execute()
        logger.info(f"Saved level-up settings for guild {guild_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save level-up settings: {e}", exc_info=True)
        return False


def format_level_up_message(template: str, user_mention: str, level: int) -> str:
    """
    Format level-up message with variables.
    
    Available variables: {user}, {level}
    """
    return template.replace('{user}', user_mention).replace('{level}', str(level))
