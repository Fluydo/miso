"""
functions/bot_profile.py
Per-guild bot profile management for Miso Bot.
"""

import logging
from typing import Optional
import discord
import config

logger = logging.getLogger("miso.functions.bot_profile")


async def fetch_guild_bot_profile(guild_id: int) -> Optional[dict]:
    """
    Fetch the custom bot profile for a specific guild from Supabase.
    
    Returns:
        dict with keys: enabled, display_name, avatar_url, banner_url, description
        None if no profile exists or Supabase not configured
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('bot_profiles').select('*').eq('guild_id', str(guild_id)).execute()
        
        if response.data and len(response.data) > 0:
            profile = response.data[0]
            logger.info(f"Fetched bot profile for guild {guild_id}: enabled={profile.get('enabled')}")
            return profile
        else:
            logger.debug(f"No bot profile found for guild {guild_id}")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch bot profile for guild {guild_id}: {e}", exc_info=True)
        return None


async def apply_guild_profile(bot: discord.Client, guild: discord.Guild) -> bool:
    """
    Apply custom bot profile for a specific guild.
    
    Args:
        bot: The Discord bot instance
        guild: The guild to apply profile for
    
    Returns:
        True if profile was applied successfully, False otherwise
    """
    profile = await fetch_guild_bot_profile(guild.id)
    
    if not profile or not profile.get('enabled'):
        logger.debug(f"No enabled profile for guild {guild.id}, using defaults")
        return False
    
    try:
        # Get the guild member object for the bot
        bot_member = guild.get_member(bot.user.id)
        if not bot_member:
            logger.warning(f"Bot is not a member of guild {guild.id}")
            return False
        
        changes_made = False
        
        # Apply display name (nickname)
        display_name = profile.get('display_name')
        if display_name and display_name != bot_member.display_name:
            try:
                await bot_member.edit(nick=display_name)
                logger.info(f"Set bot nickname to '{display_name}' in guild {guild.name} ({guild.id})")
                changes_made = True
            except discord.Forbidden:
                logger.warning(f"Missing permission to change nickname in guild {guild.name} ({guild.id})")
            except discord.HTTPException as e:
                logger.error(f"Failed to change nickname in guild {guild.name}: {e}")
        
        # Note: Avatar and banner are global settings and cannot be set per-guild
        # These would require the bot to change its global profile, which isn't practical
        # for per-guild customization. We'll keep these in the database for future use
        # or for display in the dashboard.
        
        return changes_made
    except Exception as e:
        logger.error(f"Failed to apply bot profile for guild {guild.id}: {e}", exc_info=True)
        return False


async def sync_all_guild_profiles(bot: discord.Client) -> dict:
    """
    Sync bot profiles for all guilds the bot is in.
    
    Returns:
        dict with keys: success (int), failed (int), skipped (int)
    """
    results = {"success": 0, "failed": 0, "skipped": 0}
    
    for guild in bot.guilds:
        try:
            applied = await apply_guild_profile(bot, guild)
            if applied:
                results["success"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            logger.error(f"Error syncing profile for guild {guild.id}: {e}")
            results["failed"] += 1
    
    logger.info(f"Guild profile sync complete: {results}")
    return results
