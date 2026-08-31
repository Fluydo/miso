"""
functions/supabase_sync.py
Sync bot data to Supabase for the web dashboard.
"""

import logging
from typing import Optional

import httpx

import config

logger = logging.getLogger("miso.functions.supabase_sync")


async def sync_giveaway_to_supabase(
    message_id: int,
    guild_id: int,
    channel_id: int,
    prize: str,
    winners_count: int,
    end_timestamp: float,
    host_id: int,
    active: bool = True,
    winner_discord_id: Optional[str] = None,
) -> bool:
    """Sync a giveaway to Supabase so the website can read it."""
    if not config.SUPABASE_SERVICE_KEY:
        logger.warning("SUPABASE_SERVICE_KEY not set, skipping giveaway sync")
        return False

    url = f"{config.SUPABASE_URL}/rest/v1/giveaways"
    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    from datetime import datetime, timezone

    ends_at = datetime.fromtimestamp(end_timestamp, tz=timezone.utc).isoformat()

    payload = {
        "message_id": str(message_id),
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
        "prize": prize,
        "winners_count": winners_count,
        "ends_at": ends_at,
        "active": active,
        "host": f"<@{host_id}>",
        "winner_discord_id": winner_discord_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in (200, 201):
                logger.info(f"Synced giveaway {message_id} to Supabase")
                return True
            else:
                logger.error(f"Failed to sync giveaway {message_id}: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Error syncing giveaway to Supabase: {e}")
        return False


async def sync_giveaway_entry_to_supabase(message_id: int, user_id: int, added: bool) -> bool:
    """Sync a giveaway entry to Supabase."""
    if not config.SUPABASE_SERVICE_KEY:
        return False

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    # First get the giveaway UUID from message_id
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/giveaways?message_id=eq.{message_id}&select=id",
                headers=headers,
            )
            if resp.status_code != 200 or not resp.json():
                logger.error(f"Giveaway {message_id} not found in Supabase")
                return False

            giveaway_id = resp.json()[0]["id"]

            if added:
                # Add entry
                payload = {"giveaway_id": giveaway_id, "discord_id": str(user_id)}
                resp = await client.post(
                    f"{config.SUPABASE_URL}/rest/v1/giveaway_entries",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code in (200, 201):
                    logger.info(f"Added giveaway entry for user {user_id} to Supabase")
                    return True
                else:
                    logger.error(f"Failed to add entry: {resp.status_code} {resp.text}")
                    return False
            else:
                # Remove entry
                resp = await client.delete(
                    f"{config.SUPABASE_URL}/rest/v1/giveaway_entries?giveaway_id=eq.{giveaway_id}&discord_id=eq.{user_id}",
                    headers=headers,
                )
                if resp.status_code in (200, 204):
                    logger.info(f"Removed giveaway entry for user {user_id} from Supabase")
                    return True
                else:
                    logger.error(f"Failed to remove entry: {resp.status_code} {resp.text}")
                    return False

    except Exception as e:
        logger.error(f"Error syncing giveaway entry: {e}")
        return False
