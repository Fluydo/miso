"""
Message caching system to preserve embeds, components, and attachments
so they can be displayed in delete logs even after Discord deletes them.
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import aiohttp
import discord

import config

logger = logging.getLogger("miso.message_cache")

CACHE_DIR = config.DATA_DIR / "message_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache (last 1000 messages per guild)
_cache: dict[int, dict[int, dict]] = {}  # {guild_id: {message_id: cached_data}}
MAX_CACHE_PER_GUILD = 1000


async def download_attachment(url: str, message_id: int) -> str | None:
    """Downloads an attachment and saves it locally. Returns local filename."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return None
                
                # Generate filename
                filename = url.split("/")[-1].split("?")[0]
                local_path = CACHE_DIR / f"{message_id}_{filename}"
                
                # Save file
                data = await resp.read()
                with open(local_path, "wb") as f:
                    f.write(data)
                
                return str(local_path)
    except Exception as e:
        logger.error(f"Failed to download attachment {url}: {e}")
        return None


def cache_message(message: discord.Message) -> None:
    """Cache a message with all its embeds, components, and attachments."""
    if not message.guild:
        return
    
    guild_id = message.guild.id
    if guild_id not in _cache:
        _cache[guild_id] = {}
    
    # Remove oldest if cache is full
    if len(_cache[guild_id]) >= MAX_CACHE_PER_GUILD:
        oldest_id = next(iter(_cache[guild_id]))
        _cache[guild_id].pop(oldest_id)
    
    # Serialize embeds
    embeds_data = []
    for embed in message.embeds:
        embeds_data.append(embed.to_dict())
    
    # Serialize components (buttons, select menus, etc.)
    components_data = []
    for action_row in message.components:
        row_data = {"type": action_row.type.value, "children": []}
        for child in action_row.children:
            child_dict = {"type": child.type.value}
            if hasattr(child, 'label'):
                child_dict['label'] = child.label
            if hasattr(child, 'custom_id'):
                child_dict['custom_id'] = child.custom_id
            if hasattr(child, 'url'):
                child_dict['url'] = child.url
            if hasattr(child, 'emoji'):
                if child.emoji:
                    child_dict['emoji'] = str(child.emoji)
            row_data["children"].append(child_dict)
        components_data.append(row_data)
    
    # Store attachment URLs (we'll download them asynchronously)
    attachments_data = []
    for att in message.attachments:
        attachments_data.append({
            "filename": att.filename,
            "url": att.url,
            "content_type": att.content_type,
            "size": att.size,
        })
    
    # Cache the data
    _cache[guild_id][message.id] = {
        "content": message.content,
        "embeds": embeds_data,
        "components": components_data,
        "attachments": attachments_data,
        "author_id": message.author.id,
        "author_name": message.author.display_name,
        "author_avatar": message.author.display_avatar.url,
        "author_bot": message.author.bot,
        "channel_id": message.channel.id,
        "created_at": message.created_at.isoformat(),
        "cached_at": datetime.utcnow().isoformat(),
    }
    
    # Download attachments in background
    if attachments_data:
        asyncio.create_task(_download_attachments_async(message.id, attachments_data))


async def _download_attachments_async(message_id: int, attachments_data: list[dict]) -> None:
    """Background task to download attachments."""
    for att in attachments_data:
        local_path = await download_attachment(att["url"], message_id)
        if local_path:
            att["local_path"] = local_path


def get_cached_message(guild_id: int, message_id: int) -> dict | None:
    """Retrieve cached message data."""
    if guild_id not in _cache:
        return None
    return _cache[guild_id].get(message_id)


def clear_old_cache(max_age_hours: int = 24) -> None:
    """Clear cached messages older than max_age_hours."""
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    for guild_id in list(_cache.keys()):
        for msg_id in list(_cache[guild_id].keys()):
            cached_at_str = _cache[guild_id][msg_id].get("cached_at")
            if cached_at_str:
                cached_at = datetime.fromisoformat(cached_at_str)
                if cached_at < cutoff:
                    _cache[guild_id].pop(msg_id)
        
        # Remove empty guild caches
        if not _cache[guild_id]:
            _cache.pop(guild_id)
