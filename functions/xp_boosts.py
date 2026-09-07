"""
functions/xp_boosts.py
XP boost event management - temporary XP multipliers for guilds.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import config

logger = logging.getLogger("miso.functions.xp_boosts")


async def get_active_boost(guild_id: int) -> Optional[dict]:
    """
    Get currently active XP boost for a guild.
    
    Returns:
        dict with keys: id, multiplier, started_by, start_time, end_time, reason
        None if no active boost
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        now = datetime.utcnow().isoformat()
        
        response = supabase.table('xp_boost_events').select('*').eq('guild_id', str(guild_id)).eq('is_active', True).lte('start_time', now).gte('end_time', now).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get active boost: {e}")
        return None


async def create_boost_event(guild_id: int, started_by: int, multiplier: float, duration_hours: int, reason: str = None) -> dict:
    """
    Create a new XP boost event.
    
    Args:
        guild_id: Guild ID
        started_by: User ID who started it
        multiplier: XP multiplier (e.g., 2.0 for 2x XP)
        duration_hours: How long the boost lasts
        reason: Optional reason for the boost
    
    Returns:
        dict with keys: success, message, boost_id
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'XP boosts not available'}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Check if there's already an active boost
        active = await get_active_boost(guild_id)
        if active:
            return {
                'success': False,
                'message': f'There is already an active {active["multiplier"]}x XP boost running!',
                'boost_id': None
            }
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=duration_hours)
        
        data = {
            'guild_id': str(guild_id),
            'multiplier': multiplier,
            'started_by': str(started_by),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'is_active': True,
            'reason': reason
        }
        
        response = supabase.table('xp_boost_events').insert(data).execute()
        
        if response.data and len(response.data) > 0:
            boost_id = response.data[0]['id']
            logger.info(f"Created {multiplier}x XP boost for guild {guild_id}, duration: {duration_hours}h")
            return {
                'success': True,
                'message': f'Activated {multiplier}x XP boost for {duration_hours} hours!',
                'boost_id': boost_id
            }
        
        return {'success': False, 'message': 'Failed to create boost', 'boost_id': None}
        
    except Exception as e:
        logger.error(f"Failed to create boost event: {e}", exc_info=True)
        return {'success': False, 'message': f'Error: {str(e)}', 'boost_id': None}


async def end_boost_event(guild_id: int) -> bool:
    """
    End the currently active boost event for a guild.
    
    Returns:
        True if boost was ended
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        active = await get_active_boost(guild_id)
        if not active:
            return False
        
        # Mark as inactive
        supabase.table('xp_boost_events').update({
            'is_active': False,
            'end_time': datetime.utcnow().isoformat()
        }).eq('id', active['id']).execute()
        
        logger.info(f"Ended XP boost {active['id']} for guild {guild_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to end boost event: {e}")
        return False


async def get_boost_multiplier(guild_id: int) -> float:
    """
    Get the current XP boost multiplier for a guild.
    
    Returns:
        float multiplier (1.0 if no boost, >1.0 if boost active)
    """
    boost = await get_active_boost(guild_id)
    if boost:
        return float(boost['multiplier'])
    return 1.0


async def cleanup_expired_boosts() -> int:
    """
    Cleanup expired boost events (set is_active = False).
    
    Returns:
        Number of boosts cleaned up
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return 0
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        now = datetime.utcnow().isoformat()
        
        # Find expired boosts
        response = supabase.table('xp_boost_events').select('id').eq('is_active', True).lt('end_time', now).execute()
        
        if not response.data:
            return 0
        
        # Mark them as inactive
        for boost in response.data:
            supabase.table('xp_boost_events').update({'is_active': False}).eq('id', boost['id']).execute()
        
        count = len(response.data)
        logger.info(f"Cleaned up {count} expired XP boosts")
        return count
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired boosts: {e}")
        return 0
