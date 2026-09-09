# -*- coding: utf-8 -*-
"""
functions/embed_customizations.py
Per-server embed customization - allows guilds to override embed text and colors.
"""

import json
import logging
from typing import Optional
import discord
import config

logger = logging.getLogger("miso.functions.embed_customizations")

# Registry of all customizable embeds and their fields with defaults
# Structure: { embed_key: { field_key: { label, default, type, placeholders } } }
EMBED_REGISTRY = {
    "dm_punishment": {
        "_meta": {
            "label": "Punishment DM",
            "description": "Sent to users when they are banned, kicked, muted, or warned",
            "category": "Moderation",
        },
        "description": {
            "label": "Message Body",
            "default": "You have received a **{action}** in **{server_name}**.\n\n**Reason:** {reason}",
            "type": "textarea",
            "placeholders": ["{action}", "{server_name}", "{reason}", "{duration}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#e74c3c",
            "type": "color",
            "placeholders": [],
        },
        "footer": {
            "label": "Footer Text",
            "default": "If you believe this is a mistake, please contact an admin.",
            "type": "text",
            "placeholders": ["{server_name}"],
        },
    },
    "ticket_panel": {
        "_meta": {
            "label": "Ticket Panel",
            "description": "The embed shown in the ticket creation channel",
            "category": "Tickets",
        },
        "title": {
            "label": "Panel Title",
            "default": "🎫 Support Center",
            "type": "text",
            "placeholders": ["{server_name}"],
        },
        "description": {
            "label": "Panel Description",
            "default": "Here you can talk to support, report an issue, or apply for staff.\n\nSelect a category below to open a ticket.",
            "type": "textarea",
            "placeholders": ["{server_name}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#a240f7",
            "type": "color",
            "placeholders": [],
        },
    },
    "ticket_welcome": {
        "_meta": {
            "label": "Ticket Welcome",
            "description": "Sent inside the ticket channel when a user opens a ticket",
            "category": "Tickets",
        },
        "description": {
            "label": "Welcome Message",
            "default": "Welcome {user}! Support staff will assist you shortly.\n\nPlease describe your issue in as much detail as possible.",
            "type": "textarea",
            "placeholders": ["{user}", "{ticket_number}", "{ticket_type}", "{server_name}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#a240f7",
            "type": "color",
            "placeholders": [],
        },
    },
    "level_up": {
        "_meta": {
            "label": "Level Up Message",
            "description": "Shown when a user levels up in chat",
            "category": "Levels",
        },
        "title": {
            "label": "Title",
            "default": "🎉 Level Up!",
            "type": "text",
            "placeholders": ["{user_name}", "{level}"],
        },
        "description": {
            "label": "Description",
            "default": "Congratulations {user}! You've reached **Level {level}**!",
            "type": "textarea",
            "placeholders": ["{user}", "{user_name}", "{level}", "{server_name}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#f0b232",
            "type": "color",
            "placeholders": [],
        },
    },
    "welcome": {
        "_meta": {
            "label": "Welcome Message",
            "description": "Shown when a new member joins the server",
            "category": "Welcome",
        },
        "title": {
            "label": "Title",
            "default": "Welcome to {server_name}!",
            "type": "text",
            "placeholders": ["{server_name}", "{user_name}"],
        },
        "description": {
            "label": "Description",
            "default": "Hey {user}, welcome to **{server_name}**! You are member #{member_count}.\n\nPlease read the rules and have fun!",
            "type": "textarea",
            "placeholders": ["{user}", "{user_name}", "{user_id}", "{server_name}", "{member_count}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#23a559",
            "type": "color",
            "placeholders": [],
        },
        "footer": {
            "label": "Footer Text",
            "default": "Welcome to the server!",
            "type": "text",
            "placeholders": ["{server_name}", "{member_count}"],
        },
    },
    "achievement_unlock": {
        "_meta": {
            "label": "Achievement Unlocked",
            "description": "Shown when a user unlocks an achievement",
            "category": "Achievements",
        },
        "title": {
            "label": "Title",
            "default": "🏆 Achievement Unlocked!",
            "type": "text",
            "placeholders": [],
        },
        "description": {
            "label": "Description",
            "default": "{user} just unlocked **{achievement_name}**!\n\n{achievement_description}",
            "type": "textarea",
            "placeholders": ["{user}", "{user_name}", "{achievement_name}", "{achievement_description}", "{reward_xp}", "{reward_coins}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#f0b232",
            "type": "color",
            "placeholders": [],
        },
    },
    "daily_reward": {
        "_meta": {
            "label": "Daily Reward",
            "description": "Shown when a user claims their daily reward",
            "category": "Economy",
        },
        "title": {
            "label": "Title",
            "default": "🎁 Daily Reward Claimed!",
            "type": "text",
            "placeholders": ["{user_name}"],
        },
        "description": {
            "label": "Description",
            "default": "You claimed your daily reward!\n\n🔥 Streak: **{streak} days**",
            "type": "textarea",
            "placeholders": ["{user}", "{user_name}", "{streak}", "{longest_streak}", "{xp_earned}", "{coins_earned}", "{multiplier}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#f0b232",
            "type": "color",
            "placeholders": [],
        },
    },
    "mod_action_log": {
        "_meta": {
            "label": "Mod Action Log",
            "description": "Posted to mod-log channel when a moderation action is taken",
            "category": "Moderation",
        },
        "color_ban": {
            "label": "Ban Color",
            "default": "#e74c3c",
            "type": "color",
            "placeholders": [],
        },
        "color_kick": {
            "label": "Kick Color",
            "default": "#e67e22",
            "type": "color",
            "placeholders": [],
        },
        "color_warn": {
            "label": "Warn Color",
            "default": "#f0b232",
            "type": "color",
            "placeholders": [],
        },
        "color_timeout": {
            "label": "Timeout Color",
            "default": "#9b59b6",
            "type": "color",
            "placeholders": [],
        },
        "footer": {
            "label": "Footer Text",
            "default": "Moderation Action",
            "type": "text",
            "placeholders": ["{server_name}"],
        },
    },
    "invite_stats": {
        "_meta": {
            "label": "Invite Stats",
            "description": "Shown when a user checks their invite stats",
            "category": "Invites",
        },
        "description": {
            "label": "Description",
            "default": "{user} has **{total_invites}** total invites\n✅ **{active_invites}** active · ❌ **{left_invites}** left",
            "type": "textarea",
            "placeholders": ["{user}", "{user_name}", "{total_invites}", "{active_invites}", "{left_invites}", "{server_name}"],
        },
        "color": {
            "label": "Embed Color",
            "default": "#5865f2",
            "type": "color",
            "placeholders": [],
        },
    },
}


async def get_embed_field(guild_id: int, embed_key: str, field_key: str) -> Optional[str]:
    """
    Get a custom embed field value for a guild.
    Returns None if no customization exists (use the default).
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None

    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        response = supabase.table('embed_customizations').select('value').eq(
            'guild_id', str(guild_id)
        ).eq('embed_key', embed_key).eq('field_key', field_key).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]['value']
        return None
    except Exception as e:
        logger.error(f"Failed to get embed customization: {e}")
        return None


async def get_embed_text(guild_id: int, embed_key: str, field_key: str, default: str) -> str:
    """
    Get embed text with fallback to default.
    """
    custom = await get_embed_field(guild_id, embed_key, field_key)
    return custom if custom is not None else default


async def get_embed_color(guild_id: int, embed_key: str, field_key: str = "color", default: str = "#5865f2") -> int:
    """
    Get embed color as integer with fallback to default.
    """
    custom = await get_embed_field(guild_id, embed_key, field_key)
    color_hex = custom if custom is not None else default
    try:
        return int(color_hex.replace('#', ''), 16)
    except (ValueError, AttributeError):
        return int(default.replace('#', ''), 16)


async def get_all_customizations(guild_id: int) -> dict:
    """
    Get all embed customizations for a guild as a dict.
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {}

    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        response = supabase.table('embed_customizations').select('*').eq(
            'guild_id', str(guild_id)
        ).execute()

        result = {}
        for row in (response.data or []):
            key = f"{row['embed_key']}.{row['field_key']}"
            result[key] = row['value']
        return result
    except Exception as e:
        logger.error(f"Failed to get all embed customizations: {e}")
        return {}


async def save_embed_field(guild_id: int, embed_key: str, field_key: str, value: str) -> bool:
    """
    Save a custom embed field value for a guild.
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False

    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        supabase.table('embed_customizations').upsert({
            'guild_id': str(guild_id),
            'embed_key': embed_key,
            'field_key': field_key,
            'value': value,
            'updated_at': 'now()',
        }, on_conflict='guild_id,embed_key,field_key').execute()

        logger.info(f"Saved embed customization for guild {guild_id}: {embed_key}.{field_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save embed customization: {e}")
        return False


async def delete_embed_field(guild_id: int, embed_key: str, field_key: str) -> bool:
    """
    Delete a custom embed field, reverting to the default.
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False

    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        supabase.table('embed_customizations').delete().eq(
            'guild_id', str(guild_id)
        ).eq('embed_key', embed_key).eq('field_key', field_key).execute()

        return True
    except Exception as e:
        logger.error(f"Failed to delete embed customization: {e}")
        return False


async def delete_all_embed_customizations(guild_id: int, embed_key: str) -> bool:
    """
    Delete ALL customizations for a specific embed (restore to default).
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False

    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        supabase.table('embed_customizations').delete().eq(
            'guild_id', str(guild_id)
        ).eq('embed_key', embed_key).execute()

        logger.info(f"Deleted all customizations for guild {guild_id}, embed {embed_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete embed customizations: {e}")
        return False


def format_text(template: str, **kwargs) -> str:
    """
    Format a template string with provided variables.
    Unknown placeholders are left as-is.
    """
    for key, value in kwargs.items():
        template = template.replace(f"{{{key}}}", str(value) if value is not None else "")
    return template


# ──────────────────────────────────────────────────────────────────────────────
# EMBED APPLICATION HELPERS
# These are the functions the bot cogs call at runtime.
# ──────────────────────────────────────────────────────────────────────────────


async def get_custom_embed_data(guild_id: int, embed_key: str) -> Optional[dict]:
    """
    Fetch the saved full_embed JSON for a guild+key combo.
    Returns a dict matching EmbedData structure, or None if not customized.
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return None

    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        response = (
            supabase.table('embed_customizations')
            .select('value')
            .eq('guild_id', str(guild_id))
            .eq('embed_key', embed_key)
            .eq('field_key', 'full_embed')
            .execute()
        )

        if response.data and len(response.data) > 0:
            return json.loads(response.data[0]['value'])
        return None
    except Exception as e:
        logger.debug(f"Could not load embed customization for {embed_key}: {e}")
        return None


def _parse_color(color_val) -> int:
    """Parse a color value (hex string or int) to Discord color int."""
    if isinstance(color_val, int):
        return color_val
    if isinstance(color_val, str):
        try:
            return int(color_val.lstrip('#'), 16)
        except (ValueError, AttributeError):
            pass
    return 0x5865F2  # Discord blurple fallback


def _build_embed_from_data(data: dict, **variables) -> discord.Embed:
    """
    Build a discord.Embed from a saved EmbedData dict.
    Performs variable substitution on all text fields.
    """
    def sub(text: str) -> str:
        if not text:
            return text
        for k, v in variables.items():
            text = text.replace('{' + k + '}', str(v) if v is not None else '')
        return text

    color = _parse_color(data.get('color', '#5865f2'))
    embed = discord.Embed(
        title=sub(data.get('title', '')) or None,
        description=sub(data.get('description', '')) or None,
        color=color,
    )

    # Author
    author = data.get('author', {})
    if author and author.get('name'):
        embed.set_author(
            name=sub(author['name']),
            icon_url=author.get('icon_url') or discord.utils.MISSING,
            url=author.get('url') or discord.utils.MISSING,
        )

    # Footer
    footer = data.get('footer', {})
    if footer and footer.get('text'):
        embed.set_footer(
            text=sub(footer['text']),
            icon_url=footer.get('icon_url') or discord.utils.MISSING,
        )

    # Images
    if data.get('thumbnail_url'):
        embed.set_thumbnail(url=data['thumbnail_url'])
    if data.get('image_url'):
        embed.set_image(url=data['image_url'])

    # Timestamp
    if data.get('timestamp'):
        from datetime import datetime, timezone
        embed.timestamp = datetime.now(timezone.utc)

    # Fields
    for field in data.get('fields', []):
        name = sub(field.get('name', '\u200b'))
        value = sub(field.get('value', '\u200b'))
        inline = field.get('inline', False)
        embed.add_field(name=name or '\u200b', value=value or '\u200b', inline=inline)

    return embed


async def build_custom_embed(
    guild_id: int,
    embed_key: str,
    default_embed: 'discord.Embed',
    **variables
) -> 'discord.Embed':
    """
    Build an embed for a given key.
    - If the guild has a custom embed saved, returns that (with variable substitution).
    - Otherwise returns the default_embed unchanged.

    Usage:
        embed = await build_custom_embed(
            guild.id,
            'level_up',
            default_embed,  # the embed you'd normally send
            user=member.mention,
            level=new_level,
            next_level=new_level + 1,
            server_name=guild.name,
        )
    """
    custom_data = await get_custom_embed_data(guild_id, embed_key)
    if custom_data is None:
        # No customization - use default
        return default_embed

    return _build_embed_from_data(custom_data, **variables)
