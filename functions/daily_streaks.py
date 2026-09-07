"""
functions/daily_streaks.py
Daily login rewards and streak tracking.
"""

import logging
from datetime import date, datetime
from typing import Optional
import config

logger = logging.getLogger("miso.functions.daily_streaks")


async def claim_daily_reward(guild_id: int, user_id: int) -> dict:
    """
    Claim daily reward and update streak.
    
    Returns:
        dict with keys: success, streak, bonus_xp, bonus_coins, message, was_broken
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {
            'success': False,
            'message': 'Daily rewards not available (database not configured)',
            'streak': 0,
            'bonus_xp': 0,
            'bonus_coins': 0,
            'was_broken': False
        }
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        today = date.today()
        
        # Get existing streak data
        response = supabase.table('daily_streaks').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        if response.data and len(response.data) > 0:
            streak_data = response.data[0]
            last_claim = streak_data.get('last_claim_date')
            
            if last_claim:
                last_date = datetime.fromisoformat(last_claim).date() if isinstance(last_claim, str) else last_claim
                
                # Already claimed today
                if last_date == today:
                    return {
                        'success': False,
                        'message': 'You already claimed your daily reward today! Come back tomorrow.',
                        'streak': streak_data['current_streak'],
                        'bonus_xp': 0,
                        'bonus_coins': 0,
                        'was_broken': False
                    }
                
                # Check if streak continues (claimed yesterday)
                from datetime import timedelta
                yesterday = today - timedelta(days=1)
                
                if last_date == yesterday:
                    # Streak continues!
                    new_streak = streak_data['current_streak'] + 1
                    was_broken = False
                else:
                    # Streak broken
                    new_streak = 1
                    was_broken = True
                
                new_longest = max(new_streak, streak_data['longest_streak'])
            else:
                # First time claiming
                new_streak = 1
                new_longest = 1
                was_broken = False
            
            # Update streak
            supabase.table('daily_streaks').update({
                'current_streak': new_streak,
                'longest_streak': new_longest,
                'last_claim_date': today.isoformat(),
                'total_claims': streak_data['total_claims'] + 1,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
            
        else:
            # First time ever
            new_streak = 1
            new_longest = 1
            was_broken = False
            
            supabase.table('daily_streaks').insert({
                'guild_id': str(guild_id),
                'user_id': str(user_id),
                'current_streak': new_streak,
                'longest_streak': new_longest,
                'last_claim_date': today.isoformat(),
                'total_claims': 1
            }).execute()
        
        # Calculate rewards based on streak
        base_xp = 50
        base_coins = 100
        
        # Bonus for streak milestones
        streak_multiplier = 1.0
        if new_streak >= 30:
            streak_multiplier = 3.0
        elif new_streak >= 14:
            streak_multiplier = 2.5
        elif new_streak >= 7:
            streak_multiplier = 2.0
        elif new_streak >= 3:
            streak_multiplier = 1.5
        
        bonus_xp = int(base_xp * streak_multiplier)
        bonus_coins = int(base_coins * streak_multiplier)
        
        return {
            'success': True,
            'streak': new_streak,
            'longest_streak': new_longest,
            'bonus_xp': bonus_xp,
            'bonus_coins': bonus_coins,
            'message': 'Daily reward claimed!',
            'was_broken': was_broken
        }
        
    except Exception as e:
        logger.error(f"Failed to claim daily reward: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Error claiming reward: {str(e)}',
            'streak': 0,
            'bonus_xp': 0,
            'bonus_coins': 0,
            'was_broken': False
        }


async def get_streak_data(guild_id: int, user_id: int) -> dict:
    """
    Get streak information for a user.
    
    Returns:
        dict with keys: current_streak, longest_streak, total_claims, last_claim_date, can_claim_today
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'total_claims': 0,
            'last_claim_date': None,
            'can_claim_today': False
        }
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('daily_streaks').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        if not response.data or len(response.data) == 0:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'total_claims': 0,
                'last_claim_date': None,
                'can_claim_today': True
            }
        
        streak_data = response.data[0]
        last_claim = streak_data.get('last_claim_date')
        
        can_claim = True
        if last_claim:
            last_date = datetime.fromisoformat(last_claim).date() if isinstance(last_claim, str) else last_claim
            can_claim = last_date != date.today()
        
        return {
            'current_streak': streak_data.get('current_streak', 0),
            'longest_streak': streak_data.get('longest_streak', 0),
            'total_claims': streak_data.get('total_claims', 0),
            'last_claim_date': last_claim,
            'can_claim_today': can_claim
        }
        
    except Exception as e:
        logger.error(f"Failed to get streak data: {e}")
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'total_claims': 0,
            'last_claim_date': None,
            'can_claim_today': False
        }
