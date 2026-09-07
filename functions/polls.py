"""
functions/polls.py
Poll and voting system management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
import json
import config

logger = logging.getLogger("miso.functions.polls")


async def create_poll(
    guild_id: int,
    channel_id: int,
    message_id: int,
    question: str,
    options: List[str],
    created_by: int,
    duration_hours: int = None,
    allow_multiple: bool = False
) -> dict:
    """
    Create a new poll.
    
    Args:
        guild_id: Guild ID
        channel_id: Channel ID where poll is posted
        message_id: Message ID of the poll
        question: Poll question
        options: List of option strings
        created_by: User ID who created it
        duration_hours: How long poll lasts (None = no expiry)
        allow_multiple: Allow voting for multiple options
    
    Returns:
        dict with keys: success, message, poll_id
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'Polls not available', 'poll_id': None}
    
    if len(options) < 2:
        return {'success': False, 'message': 'Polls need at least 2 options!', 'poll_id': None}
    
    if len(options) > 10:
        return {'success': False, 'message': 'Polls can have maximum 10 options!', 'poll_id': None}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Format options as JSONB
        options_json = []
        for i, text in enumerate(options):
            options_json.append({
                'id': i,
                'text': text,
                'votes': []
            })
        
        ends_at = None
        if duration_hours:
            ends_at = (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat()
        
        data = {
            'guild_id': str(guild_id),
            'channel_id': str(channel_id),
            'message_id': str(message_id),
            'question': question,
            'options': json.dumps(options_json),
            'created_by': str(created_by),
            'ends_at': ends_at,
            'is_active': True,
            'allow_multiple': allow_multiple
        }
        
        response = supabase.table('polls').insert(data).execute()
        
        if response.data and len(response.data) > 0:
            poll_id = response.data[0]['id']
            logger.info(f"Created poll {poll_id} in guild {guild_id}")
            return {
                'success': True,
                'message': 'Poll created!',
                'poll_id': poll_id
            }
        
        return {'success': False, 'message': 'Failed to create poll', 'poll_id': None}
        
    except Exception as e:
        logger.error(f"Failed to create poll: {e}", exc_info=True)
        return {'success': False, 'message': f'Error: {str(e)}', 'poll_id': None}


async def get_poll(message_id: int) -> Optional[dict]:
    """Get poll by message ID."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('polls').select('*').eq('message_id', str(message_id)).execute()
        
        if response.data and len(response.data) > 0:
            poll = response.data[0]
            # Parse options JSON
            if isinstance(poll['options'], str):
                poll['options'] = json.loads(poll['options'])
            return poll
        return None
    except Exception as e:
        logger.error(f"Failed to get poll: {e}")
        return None


async def vote_poll(message_id: int, user_id: int, option_id: int) -> dict:
    """
    Vote on a poll.
    
    Returns:
        dict with keys: success, message, already_voted
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'Polls not available', 'already_voted': False}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        poll = await get_poll(message_id)
        if not poll:
            return {'success': False, 'message': 'Poll not found!', 'already_voted': False}
        
        if not poll['is_active']:
            return {'success': False, 'message': 'This poll has ended!', 'already_voted': False}
        
        # Check if poll has expired
        if poll.get('ends_at'):
            ends_at = datetime.fromisoformat(poll['ends_at'])
            if datetime.utcnow() > ends_at:
                # End the poll
                await end_poll(message_id)
                return {'success': False, 'message': 'This poll has ended!', 'already_voted': False}
        
        options = poll['options']
        user_id_str = str(user_id)
        
        # Check if option exists
        option = None
        for opt in options:
            if opt['id'] == option_id:
                option = opt
                break
        
        if not option:
            return {'success': False, 'message': 'Invalid option!', 'already_voted': False}
        
        # Check if user already voted
        already_voted_this_option = user_id_str in option['votes']
        
        if not poll.get('allow_multiple', False):
            # Single-vote mode: remove from all other options
            for opt in options:
                if user_id_str in opt['votes']:
                    if opt['id'] == option_id:
                        # Already voted for this one
                        return {'success': False, 'message': 'You already voted for this option!', 'already_voted': True}
                    else:
                        opt['votes'].remove(user_id_str)
        
        # Add vote
        if not already_voted_this_option:
            option['votes'].append(user_id_str)
        
        # Update database
        supabase.table('polls').update({
            'options': json.dumps(options)
        }).eq('id', poll['id']).execute()
        
        logger.info(f"User {user_id} voted for option {option_id} on poll {poll['id']}")
        return {'success': True, 'message': 'Vote recorded!', 'already_voted': False}
        
    except Exception as e:
        logger.error(f"Failed to vote on poll: {e}", exc_info=True)
        return {'success': False, 'message': f'Error: {str(e)}', 'already_voted': False}


async def end_poll(message_id: int) -> bool:
    """End a poll (mark as inactive)."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        supabase.table('polls').update({
            'is_active': False
        }).eq('message_id', str(message_id)).execute()
        
        logger.info(f"Ended poll with message ID {message_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to end poll: {e}")
        return False


async def get_active_polls(guild_id: int) -> List[dict]:
    """Get all active polls for a guild."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('polls').select('*').eq('guild_id', str(guild_id)).eq('is_active', True).order('created_at', desc=True).execute()
        
        if response.data:
            polls = []
            for poll in response.data:
                if isinstance(poll['options'], str):
                    poll['options'] = json.loads(poll['options'])
                polls.append(poll)
            return polls
        return []
    except Exception as e:
        logger.error(f"Failed to get active polls: {e}")
        return []
