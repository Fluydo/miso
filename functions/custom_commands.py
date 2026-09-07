"""
functions/custom_commands.py
Custom command management - allows guilds to create custom commands.
"""

import logging
from typing import Optional, List
import config

logger = logging.getLogger("miso.functions.custom_commands")


async def get_custom_command(guild_id: int, trigger: str) -> Optional[dict]:
    """
    Get a custom command by trigger.
    
    Returns:
        dict with command data or None if not found
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('custom_commands').select('*').eq('guild_id', str(guild_id)).eq('trigger', trigger.lower()).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get custom command: {e}")
        return None


async def get_all_custom_commands(guild_id: int) -> List[dict]:
    """
    Get all custom commands for a guild.
    
    Returns:
        List of command dicts
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('custom_commands').select('*').eq('guild_id', str(guild_id)).order('trigger').execute()
        
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Failed to get custom commands: {e}")
        return []


async def create_custom_command(
    guild_id: int,
    trigger: str,
    created_by: int,
    response_text: str = None,
    embed_title: str = None,
    embed_description: str = None,
    embed_color: int = None,
    embed_image_url: str = None
) -> dict:
    """
    Create a new custom command.
    
    Returns:
        dict with keys: success, message, command_id
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'Custom commands not available', 'command_id': None}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Check if command already exists
        existing = await get_custom_command(guild_id, trigger)
        if existing:
            return {
                'success': False,
                'message': f'Command `{trigger}` already exists!',
                'command_id': None
            }
        
        # Validate trigger (alphanumeric + hyphens/underscores only)
        if not trigger.replace('-', '').replace('_', '').isalnum():
            return {
                'success': False,
                'message': 'Trigger must contain only letters, numbers, hyphens, and underscores!',
                'command_id': None
            }
        
        # At least one response field must be provided
        if not response_text and not embed_title and not embed_description:
            return {
                'success': False,
                'message': 'You must provide at least one response (text, embed title, or embed description)!',
                'command_id': None
            }
        
        data = {
            'guild_id': str(guild_id),
            'trigger': trigger.lower(),
            'created_by': str(created_by),
            'response_text': response_text,
            'embed_title': embed_title,
            'embed_description': embed_description,
            'embed_color': embed_color,
            'embed_image_url': embed_image_url
        }
        
        response = supabase.table('custom_commands').insert(data).execute()
        
        if response.data and len(response.data) > 0:
            command_id = response.data[0]['id']
            logger.info(f"Created custom command '{trigger}' in guild {guild_id}")
            return {
                'success': True,
                'message': f'Custom command `{trigger}` created successfully!',
                'command_id': command_id
            }
        
        return {'success': False, 'message': 'Failed to create command', 'command_id': None}
        
    except Exception as e:
        logger.error(f"Failed to create custom command: {e}", exc_info=True)
        return {'success': False, 'message': f'Error: {str(e)}', 'command_id': None}


async def update_custom_command(
    guild_id: int,
    trigger: str,
    response_text: str = None,
    embed_title: str = None,
    embed_description: str = None,
    embed_color: int = None,
    embed_image_url: str = None
) -> bool:
    """
    Update an existing custom command.
    
    Returns:
        True if successful
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Check if command exists
        existing = await get_custom_command(guild_id, trigger)
        if not existing:
            return False
        
        data = {}
        if response_text is not None:
            data['response_text'] = response_text
        if embed_title is not None:
            data['embed_title'] = embed_title
        if embed_description is not None:
            data['embed_description'] = embed_description
        if embed_color is not None:
            data['embed_color'] = embed_color
        if embed_image_url is not None:
            data['embed_image_url'] = embed_image_url
        
        if not data:
            return False
        
        supabase.table('custom_commands').update(data).eq('id', existing['id']).execute()
        logger.info(f"Updated custom command '{trigger}' in guild {guild_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update custom command: {e}")
        return False


async def delete_custom_command(guild_id: int, trigger: str) -> bool:
    """
    Delete a custom command.
    
    Returns:
        True if successful
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Check if command exists
        existing = await get_custom_command(guild_id, trigger)
        if not existing:
            return False
        
        supabase.table('custom_commands').delete().eq('id', existing['id']).execute()
        logger.info(f"Deleted custom command '{trigger}' from guild {guild_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete custom command: {e}")
        return False
