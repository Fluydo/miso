"""
functions/voice_xp.py
Voice channel XP tracking and rewards.
"""

import logging
from datetime import datetime
from typing import Optional
import config

logger = logging.getLogger("miso.functions.voice_xp")


async def get_voice_xp_settings(guild_id: int) -> dict:
    """
    Get voice XP settings for a guild.
    
    Returns:
        dict with keys: enabled, xp_per_minute, streaming_multiplier, video_multiplier, min_members_required
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {
            'enabled': True,
            'xp_per_minute': 2,
            'streaming_multiplier': 1.5,
            'video_multiplier': 1.25,
            'min_members_required': 2
        }
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('voice_xp_settings').select('*').eq('guild_id', str(guild_id)).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            # Return defaults
            return {
                'enabled': True,
                'xp_per_minute': 2,
                'streaming_multiplier': 1.5,
                'video_multiplier': 1.25,
                'min_members_required': 2
            }
    except Exception as e:
        logger.error(f"Failed to fetch voice XP settings for guild {guild_id}: {e}")
        return {
            'enabled': True,
            'xp_per_minute': 2,
            'streaming_multiplier': 1.5,
            'video_multiplier': 1.25,
            'min_members_required': 2
        }


async def start_voice_session(guild_id: int, user_id: int, channel_id: int, is_streaming: bool = False, is_video: bool = False) -> Optional[int]:
    """
    Start tracking a voice session.
    
    Returns:
        Session ID if successful, None otherwise
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        data = {
            'guild_id': str(guild_id),
            'user_id': str(user_id),
            'channel_id': str(channel_id),
            'joined_at': datetime.utcnow().isoformat(),
            'was_streaming': is_streaming,
            'was_video': is_video,
        }
        
        response = supabase.table('voice_sessions').insert(data).execute()
        
        if response.data and len(response.data) > 0:
            session_id = response.data[0]['id']
            logger.debug(f"Started voice session {session_id} for user {user_id} in guild {guild_id}")
            return session_id
        return None
    except Exception as e:
        logger.error(f"Failed to start voice session: {e}")
        return None


async def end_voice_session(guild_id: int, user_id: int) -> Optional[int]:
    """
    End a voice session and calculate XP earned.
    
    Returns:
        XP earned, or None if error
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Find active session
        response = supabase.table('voice_sessions').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).is_('left_at', 'null').execute()
        
        if not response.data or len(response.data) == 0:
            logger.debug(f"No active voice session found for user {user_id} in guild {guild_id}")
            return None
        
        session = response.data[0]
        session_id = session['id']
        joined_at = datetime.fromisoformat(session['joined_at'].replace('Z', '+00:00'))
        left_at = datetime.utcnow()
        duration_seconds = int((left_at - joined_at).total_seconds())
        
        # Calculate XP
        settings = await get_voice_xp_settings(guild_id)
        
        if not settings['enabled'] or duration_seconds < 60:
            # Less than 1 minute, no XP
            supabase.table('voice_sessions').update({
                'left_at': left_at.isoformat(),
                'duration_seconds': duration_seconds,
                'xp_earned': 0
            }).eq('id', session_id).execute()
            return 0
        
        minutes = duration_seconds / 60
        base_xp = int(minutes * settings['xp_per_minute'])
        
        # Apply multipliers
        multiplier = 1.0
        if session['was_streaming']:
            multiplier *= settings['streaming_multiplier']
        if session['was_video']:
            multiplier *= settings['video_multiplier']
        
        xp_earned = int(base_xp * multiplier)
        
        # Update session
        supabase.table('voice_sessions').update({
            'left_at': left_at.isoformat(),
            'duration_seconds': duration_seconds,
            'xp_earned': xp_earned
        }).eq('id', session_id).execute()
        
        logger.info(f"Ended voice session {session_id}: {duration_seconds}s = {xp_earned} XP (multiplier: {multiplier}x)")
        return xp_earned
        
    except Exception as e:
        logger.error(f"Failed to end voice session: {e}", exc_info=True)
        return None


async def update_voice_session_status(guild_id: int, user_id: int, is_streaming: bool, is_video: bool):
    """
    Update streaming/video status for an active voice session.
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Update active session
        supabase.table('voice_sessions').update({
            'was_streaming': is_streaming,
            'was_video': is_video
        }).eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).is_('left_at', 'null').execute()
        
    except Exception as e:
        logger.error(f"Failed to update voice session status: {e}")


async def get_user_voice_stats(guild_id: int, user_id: int) -> dict:
    """
    Get voice statistics for a user.
    
    Returns:
        dict with keys: total_minutes, total_xp, session_count
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'total_minutes': 0, 'total_xp': 0, 'session_count': 0}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('voice_sessions').select('duration_seconds, xp_earned').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).not_.is_('left_at', 'null').execute()
        
        if not response.data:
            return {'total_minutes': 0, 'total_xp': 0, 'session_count': 0}
        
        total_seconds = sum(s['duration_seconds'] or 0 for s in response.data)
        total_xp = sum(s['xp_earned'] or 0 for s in response.data)
        
        return {
            'total_minutes': int(total_seconds / 60),
            'total_xp': total_xp,
            'session_count': len(response.data)
        }
    except Exception as e:
        logger.error(f"Failed to fetch voice stats: {e}")
        return {'total_minutes': 0, 'total_xp': 0, 'session_count': 0}
