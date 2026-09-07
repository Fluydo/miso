"""
functions/achievements.py
Achievement system with auto-unlocking and rewards.
"""

import logging
from typing import List, Optional
import config

logger = logging.getLogger("miso.functions.achievements")


async def get_all_achievements() -> List[dict]:
    """Get all available achievements."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('achievements').select('*').execute()
        
        if response.data:
            return response.data
        return []
    except Exception as e:
        logger.error(f"Failed to fetch achievements: {e}")
        return []


async def get_user_achievements(guild_id: int, user_id: int) -> List[dict]:
    """Get achievements unlocked by user."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('user_achievements').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        if response.data:
            return response.data
        return []
    except Exception as e:
        logger.error(f"Failed to fetch user achievements: {e}")
        return []


async def unlock_achievement(guild_id: int, user_id: int, achievement_id: str) -> Optional[dict]:
    """
    Unlock an achievement for a user.
    
    Returns:
        Achievement data if newly unlocked, None if already unlocked or error
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Check if already unlocked
        existing = supabase.table('user_achievements').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).eq('achievement_id', achievement_id).execute()
        
        if existing.data and len(existing.data) > 0:
            logger.debug(f"Achievement {achievement_id} already unlocked for user {user_id}")
            return None
        
        # Get achievement details
        achievement = supabase.table('achievements').select('*').eq('id', achievement_id).execute()
        
        if not achievement.data or len(achievement.data) == 0:
            logger.warning(f"Achievement {achievement_id} not found")
            return None
        
        achievement_data = achievement.data[0]
        
        # Unlock it
        supabase.table('user_achievements').insert({
            'guild_id': str(guild_id),
            'user_id': str(user_id),
            'achievement_id': achievement_id
        }).execute()
        
        logger.info(f"Unlocked achievement {achievement_id} for user {user_id} in guild {guild_id}")
        return achievement_data
        
    except Exception as e:
        logger.error(f"Failed to unlock achievement: {e}", exc_info=True)
        return None


async def check_and_unlock_achievements(guild_id: int, user_id: int) -> List[dict]:
    """
    Check all achievements and unlock any that the user qualifies for.
    
    Returns:
        List of newly unlocked achievements
    """
    newly_unlocked = []
    
    try:
        # Get user stats
        from functions.levels import get_user_level
        from functions.economy import get_balance
        from functions.daily_streaks import get_streak_data
        from functions.voice_xp import get_user_voice_stats
        
        level, xp, _, _ = get_user_level(guild_id, user_id)
        balance = await get_balance(guild_id, user_id)
        streak = await get_streak_data(guild_id, user_id)
        voice_stats = await get_user_voice_stats(guild_id, user_id)
        
        # Get all achievements
        all_achievements = await get_all_achievements()
        unlocked = await get_user_achievements(guild_id, user_id)
        unlocked_ids = [a['achievement_id'] for a in unlocked]
        
        # Check each achievement
        for achievement in all_achievements:
            if achievement['id'] in unlocked_ids:
                continue
            
            req_type = achievement['requirement_type']
            req_value = achievement['requirement_value']
            qualified = False
            
            # Check requirements
            if req_type == 'level_reached':
                qualified = level >= req_value
            elif req_type == 'message_count':
                # This would need message tracking - skip for now
                pass
            elif req_type == 'coins_earned':
                qualified = balance.get('total_earned', 0) >= req_value
            elif req_type == 'streak_days':
                qualified = streak.get('current_streak', 0) >= req_value
            elif req_type == 'voice_time':
                qualified = voice_stats.get('total_minutes', 0) >= req_value
            
            if qualified:
                unlocked_ach = await unlock_achievement(guild_id, user_id, achievement['id'])
                if unlocked_ach:
                    newly_unlocked.append(unlocked_ach)
        
        return newly_unlocked
        
    except Exception as e:
        logger.error(f"Failed to check achievements: {e}", exc_info=True)
        return []


async def get_achievement_progress(guild_id: int, user_id: int) -> dict:
    """
    Get user's achievement progress stats.
    
    Returns:
        dict with keys: unlocked_count, total_count, completion_percentage
    """
    try:
        all_achievements = await get_all_achievements()
        user_achievements = await get_user_achievements(guild_id, user_id)
        
        total = len(all_achievements)
        unlocked = len(user_achievements)
        percentage = (unlocked / total * 100) if total > 0 else 0
        
        return {
            'unlocked_count': unlocked,
            'total_count': total,
            'completion_percentage': round(percentage, 1)
        }
    except Exception as e:
        logger.error(f"Failed to get achievement progress: {e}")
        return {'unlocked_count': 0, 'total_count': 0, 'completion_percentage': 0}


async def award_achievement_rewards(guild_id: int, user_id: int, achievement: dict) -> None:
    """Award coins and XP for unlocking an achievement."""
    try:
        if achievement.get('reward_xp', 0) > 0:
            from functions.levels import add_xp_raw
            add_xp_raw(guild_id, user_id, achievement['reward_xp'])
            logger.info(f"Awarded {achievement['reward_xp']} XP for achievement {achievement['id']}")
        
        if achievement.get('reward_coins', 0) > 0:
            from functions.economy import add_coins
            await add_coins(guild_id, user_id, achievement['reward_coins'], f"achievement: {achievement['name']}")
            logger.info(f"Awarded {achievement['reward_coins']} coins for achievement {achievement['id']}")
    except Exception as e:
        logger.error(f"Failed to award achievement rewards: {e}")
