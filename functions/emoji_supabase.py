"""
functions/emoji_supabase.py
Sync Discord emojis to Supabase for web dashboard access.
"""

import logging
from typing import Optional
import httpx
import discord

import config

logger = logging.getLogger("miso.emoji_supabase")


async def sync_guild_emojis(guild: discord.Guild) -> bool:
    """
    Sync all emojis from a Discord guild to Supabase.
    Creates/updates emoji records in the 'emojis' table.
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        logger.warning("Supabase not configured, skipping emoji sync")
        return False

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    emoji_data = []
    for emoji in guild.emojis:
        emoji_data.append({
            "guild_id": str(guild.id),
            "emoji_id": str(emoji.id),
            "emoji_name": emoji.name,
            "emoji_animated": emoji.animated,
            "emoji_url": str(emoji.url),
        })

    if not emoji_data:
        logger.info(f"No emojis found in guild {guild.id}")
        return True

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # First, delete old emojis for this guild
            delete_resp = await client.delete(
                f"{config.SUPABASE_URL}/rest/v1/emojis?guild_id=eq.{guild.id}",
                headers=headers,
            )
            
            if delete_resp.status_code not in (200, 204):
                logger.warning(f"Failed to delete old emojis: {delete_resp.status_code}")

            # Insert new emoji data
            insert_resp = await client.post(
                f"{config.SUPABASE_URL}/rest/v1/emojis",
                json=emoji_data,
                headers=headers,
            )

            if insert_resp.status_code in (200, 201):
                logger.info(f"Synced {len(emoji_data)} emojis for guild {guild.id}")
                return True
            else:
                logger.error(f"Failed to sync emojis: {insert_resp.status_code} - {insert_resp.text}")
                return False

        except Exception as e:
            logger.error(f"Error syncing emojis: {e}", exc_info=True)
            return False


async def get_guild_emojis(guild_id: int) -> list[dict]:
    """
    Fetch all emojis for a guild from Supabase.
    Returns list of emoji dicts with id, name, animated, url.
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/emojis?guild_id=eq.{guild_id}&select=emoji_id,emoji_name,emoji_animated,emoji_url",
                headers=headers,
            )

            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "id": e["emoji_id"],
                        "name": e["emoji_name"],
                        "animated": e["emoji_animated"],
                        "url": e["emoji_url"],
                    }
                    for e in data
                ]
            else:
                logger.error(f"Failed to fetch emojis: {resp.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching emojis: {e}", exc_info=True)
            return []
