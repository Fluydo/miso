"""
functions/role_colors.py
Bot role color management with gradient presets.
"""

import logging
import random
from typing import Optional, Tuple
import config

logger = logging.getLogger("miso.functions.role_colors")

# Curated color gradient pairs that work well together
# Format: (color1_hex, color2_hex, name)
COLOR_GRADIENTS = [
    # Blues
    (0x3B82F6, 0x60A5FA, "Ocean Blue"),
    (0x1E40AF, 0x3B82F6, "Deep Blue"),
    (0x0EA5E9, 0x38BDF8, "Sky Blue"),
    
    # Purples & Pinks
    (0x8B5CF6, 0xA78BFA, "Soft Purple"),
    (0x6366F1, 0x818CF8, "Indigo"),
    (0xA855F7, 0xC084FC, "Bright Purple"),
    (0xEC4899, 0xF472B6, "Hot Pink"),
    (0xDB2777, 0xEC4899, "Deep Pink"),
    
    # Blue to Purple transitions
    (0x3B82F6, 0x8B5CF6, "Blue Purple"),
    (0x6366F1, 0xA855F7, "Indigo Purple"),
    (0x0EA5E9, 0xC084FC, "Cyan Purple"),
    
    # Greens
    (0x10B981, 0x34D399, "Emerald"),
    (0x059669, 0x10B981, "Deep Green"),
    (0x22C55E, 0x4ADE80, "Lime"),
    (0x14B8A6, 0x2DD4BF, "Teal"),
    
    # Green to Blue transitions  
    (0x10B981, 0x3B82F6, "Green Blue"),
    (0x14B8A6, 0x0EA5E9, "Teal Cyan"),
    
    # Reds & Oranges
    (0xEF4444, 0xF87171, "Red"),
    (0xDC2626, 0xEF4444, "Deep Red"),
    (0xF59E0B, 0xFBBF24, "Amber"),
    (0xEA580C, 0xF97316, "Orange"),
    
    # Red to Purple transitions
    (0xDC2626, 0xDB2777, "Red Pink"),
    (0xF97316, 0xEC4899, "Orange Pink"),
    
    # Yellow & Gold (careful with these - often too bright)
    (0xEAB308, 0xFBBF24, "Gold"),
    (0xF59E0B, 0xF59E0B, "Solid Amber"), # Same color for solid
    
    # Cyan & Aqua
    (0x06B6D4, 0x22D3EE, "Cyan"),
    (0x0891B2, 0x06B6D4, "Dark Cyan"),
    
    # Special gradients
    (0x8B5CF6, 0xEC4899, "Purple Pink"),
    (0x3B82F6, 0x10B981, "Blue Green"),
    (0xF59E0B, 0xEF4444, "Sunset"),
    (0x6366F1, 0xEC4899, "Neon"),
]


def get_random_gradient() -> Tuple[int, int, str]:
    """
    Get a random color gradient from curated list.
    
    Returns:
        Tuple of (color1, color2, gradient_name)
    """
    return random.choice(COLOR_GRADIENTS)


def get_gradient_by_name(name: str) -> Optional[Tuple[int, int, str]]:
    """
    Get a specific gradient by name.
    
    Args:
        name: The gradient name (case insensitive)
    
    Returns:
        Tuple of (color1, color2, gradient_name) or None if not found
    """
    name_lower = name.lower()
    for color1, color2, grad_name in COLOR_GRADIENTS:
        if grad_name.lower() == name_lower:
            return (color1, color2, grad_name)
    return None


async def fetch_bot_role_colors(guild_id: int) -> Optional[dict]:
    """
    Fetch bot role color settings from database.
    
    Returns:
        dict with keys: role_id, color1, color2
        None if not set or error
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('bot_role_colors').select('*').eq('guild_id', str(guild_id)).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to fetch bot role colors for guild {guild_id}: {e}")
        return None


async def save_bot_role_colors(guild_id: int, role_id: int, color1: int, color2: int) -> bool:
    """
    Save bot role color settings to database.
    
    Args:
        guild_id: Guild ID
        role_id: Role ID to color
        color1: First gradient color
        color2: Second gradient color
    
    Returns:
        True if saved successfully
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        data = {
            'guild_id': str(guild_id),
            'role_id': str(role_id),
            'color1': color1,
            'color2': color2,
        }
        
        supabase.table('bot_role_colors').upsert(data, on_conflict='guild_id').execute()
        logger.info(f"Saved bot role colors for guild {guild_id}: role={role_id}, colors=({hex(color1)}, {hex(color2)})")
        return True
    except Exception as e:
        logger.error(f"Failed to save bot role colors: {e}", exc_info=True)
        return False


def get_all_gradients() -> list:
    """
    Get all available gradients with their names.
    
    Returns:
        List of dicts with keys: name, color1, color2, color1_hex, color2_hex
    """
    return [
        {
            'name': name,
            'color1': color1,
            'color2': color2,
            'color1_hex': f'#{color1:06X}',
            'color2_hex': f'#{color2:06X}',
        }
        for color1, color2, name in COLOR_GRADIENTS
    ]
