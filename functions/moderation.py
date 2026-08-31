import json
import logging
from datetime import datetime, timezone
import discord

import config

logger = logging.getLogger("miso.moderation_functions")

FORUM_THREAD_CONFIG = {
    "moderation": {
        "name": "🔨・moderation",
        "desc": "Logs for bans, tempbans, kicks, timeouts, warnings, and unbans will be recorded here.",
    },
    "messages": {
        "name": "💬・messages",
        "desc": "Logs for deleted and edited messages will be recorded here.",
    },
    "members": {
        "name": "👥・members",
        "desc": "Logs for member joins, leaves, and account age notices will be recorded here.",
    },
    "profiles": {
        "name": "🏷️・profiles",
        "desc": "Logs for member nickname changes, role updates, and username updates will be recorded here.",
    },
    "server": {
        "name": "📁・server events",
        "desc": "Logs for channel updates, role modifications, and server settings will be recorded here.",
    },
}


# ==========================================
# FILE SYSTEM INITIALIZATION
# ==========================================

def _ensure_data_files() -> None:
    """Ensure data directory and JSON files exist."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.WARNINGS_FILE.exists():
        with open(config.WARNINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    if not config.TEMPBANS_FILE.exists():
        with open(config.TEMPBANS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    if not config.SETTINGS_FILE.exists():
        with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


# ==========================================
# GUILD SETTINGS (MOD LOG CHANNEL, ETC.)
# ==========================================

def load_guild_settings() -> dict[str, dict]:
    """Loads all per-guild configurations from disk."""
    _ensure_data_files()
    try:
        with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading guild settings file: {e}. Resetting to empty.")
        return {}


def save_guild_settings(settings: dict[str, dict]) -> None:
    """Saves guild configuration dictionary to disk."""
    _ensure_data_files()
    try:
        with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Error saving guild settings: {e}")


def get_mod_log_channel_id(guild_id: int) -> int | None:
    """Retrieves the configured mod log channel ID for a specific guild."""
    settings = load_guild_settings()
    guild_key = str(guild_id)
    return settings.get(guild_key, {}).get("mod_log_channel_id")


def set_mod_log_channel_id(guild_id: int, channel_id: int | None) -> None:
    """Sets or clears the mod log channel ID for a guild."""
    settings = load_guild_settings()
    guild_key = str(guild_id)

    if guild_key not in settings:
        settings[guild_key] = {}

    settings[guild_key]["mod_log_channel_id"] = channel_id
    save_guild_settings(settings)


# ==========================================
# IMAGE-ONLY CHANNELS
# ==========================================

def get_image_channels(guild_id: int) -> list[int]:
    """Returns the list of image-only channel IDs for the guild."""
    settings = load_guild_settings()
    return settings.get(str(guild_id), {}).get("image_channels", [])


def add_image_channel(guild_id: int, channel_id: int) -> bool:
    """Registers a channel as image-only. Returns False if already registered."""
    settings = load_guild_settings()
    key = str(guild_id)
    if key not in settings:
        settings[key] = {}
    channels = settings[key].setdefault("image_channels", [])
    if channel_id in channels:
        return False
    channels.append(channel_id)
    save_guild_settings(settings)
    return True


def remove_image_channel(guild_id: int, channel_id: int) -> bool:
    """Unregisters an image-only channel. Returns False if it wasn't registered."""
    settings = load_guild_settings()
    key = str(guild_id)
    channels = settings.get(key, {}).get("image_channels", [])
    if channel_id not in channels:
        return False
    channels.remove(channel_id)
    settings[key]["image_channels"] = channels
    save_guild_settings(settings)
    return True


# ==========================================
# COUNTING CHANNELS
# ==========================================

def get_counting_config(guild_id: int) -> dict:
    """
    Returns counting config for the guild.
    Keys: channel_id (int|None), enabled (bool), last_number (int), last_user_id (int|None)
    """
    settings = load_guild_settings()
    return settings.get(str(guild_id), {}).get("counting", {
        "channel_id": None,
        "enabled": False,
        "last_number": 0,
        "last_user_id": None,
    })


def set_counting_channel(guild_id: int, channel_id: int) -> None:
    """Sets the counting channel and resets the count."""
    settings = load_guild_settings()
    key = str(guild_id)
    if key not in settings:
        settings[key] = {}
    settings[key]["counting"] = {
        "channel_id": channel_id,
        "enabled": True,
        "last_number": 0,
        "last_user_id": None,
    }
    save_guild_settings(settings)


def set_counting_enabled(guild_id: int, enabled: bool) -> None:
    """Toggles counting enforcement on or off."""
    settings = load_guild_settings()
    key = str(guild_id)
    if key not in settings:
        settings[key] = {}
    cfg = settings[key].setdefault("counting", {
        "channel_id": None,
        "enabled": False,
        "last_number": 0,
        "last_user_id": None,
    })
    cfg["enabled"] = enabled
    save_guild_settings(settings)


def update_counting_state(guild_id: int, last_number: int, last_user_id: int) -> None:
    """Advances the count after a valid message."""
    settings = load_guild_settings()
    key = str(guild_id)
    cfg = settings.get(key, {}).get("counting", {})
    cfg["last_number"] = last_number
    cfg["last_user_id"] = last_user_id
    if key not in settings:
        settings[key] = {}
    settings[key]["counting"] = cfg
    save_guild_settings(settings)


def reset_counting(guild_id: int) -> None:
    """Resets the count back to 0 (called after a wrong number)."""
    settings = load_guild_settings()
    key = str(guild_id)
    cfg = settings.get(key, {}).get("counting", {})
    cfg["last_number"] = 0
    cfg["last_user_id"] = None
    if key not in settings:
        settings[key] = {}
    settings[key]["counting"] = cfg
    save_guild_settings(settings)


# ==========================================
# WARNINGS STORAGE
# ==========================================

def load_warnings() -> dict[str, list[dict]]:
    """Loads warnings from JSON with error recovery."""
    _ensure_data_files()
    try:
        with open(config.WARNINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading warnings file: {e}. Resetting to empty.")
        return {}


def save_warnings(data: dict[str, list[dict]]) -> None:
    """Saves warnings dictionary to JSON safely."""
    _ensure_data_files()
    try:
        with open(config.WARNINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Error saving warnings: {e}")


def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
    """Adds a warning for a user and returns their new total warning count."""
    warnings_data = load_warnings()
    guild_key = str(guild_id)
    user_key = str(user_id)

    if guild_key not in warnings_data:
        warnings_data[guild_key] = {}
    if user_key not in warnings_data[guild_key]:
        warnings_data[guild_key][user_key] = []

    warning_entry = {
        "moderator_id": moderator_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    warnings_data[guild_key][user_key].append(warning_entry)
    save_warnings(warnings_data)
    return len(warnings_data[guild_key][user_key])


def get_warnings(guild_id: int, user_id: int) -> list[dict]:
    """Retrieves all warnings for a user in a specific guild."""
    warnings_data = load_warnings()
    guild_key = str(guild_id)
    user_key = str(user_id)
    return warnings_data.get(guild_key, {}).get(user_key, [])


def clear_warnings(guild_id: int, user_id: int) -> int:
    """Removes all warnings for a user in a specific guild."""
    warnings_data = load_warnings()
    guild_key = str(guild_id)
    user_key = str(user_id)

    if guild_key in warnings_data and user_key in warnings_data[guild_key]:
        count = len(warnings_data[guild_key][user_key])
        del warnings_data[guild_key][user_key]
        save_warnings(warnings_data)
        return count
    return 0


# ==========================================
# TEMPORARY BANS STORAGE
# ==========================================

def load_tempbans() -> list[dict]:
    """Loads all active temporary bans from disk."""
    _ensure_data_files()
    try:
        with open(config.TEMPBANS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading tempbans file: {e}. Resetting.")
        return []


def save_tempbans(tempbans: list[dict]) -> None:
    """Saves tempbans list to disk."""
    _ensure_data_files()
    try:
        with open(config.TEMPBANS_FILE, "w", encoding="utf-8") as f:
            json.dump(tempbans, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Error saving tempbans: {e}")


def add_tempban(guild_id: int, user_id: int, unban_timestamp: float, reason: str) -> None:
    """Registers a temporary ban record."""
    tempbans = load_tempbans()
    tempbans = [b for b in tempbans if not (b.get("guild_id") == guild_id and b.get("user_id") == user_id)]
    tempbans.append({
        "guild_id": guild_id,
        "user_id": user_id,
        "unban_timestamp": unban_timestamp,
        "reason": reason,
    })
    save_tempbans(tempbans)


def remove_tempban(guild_id: int, user_id: int) -> None:
    """Removes a tempban record after unbanning."""
    tempbans = load_tempbans()
    new_tempbans = [b for b in tempbans if not (b.get("guild_id") == guild_id and b.get("user_id") == user_id)]
    save_tempbans(new_tempbans)


def get_expired_tempbans() -> list[dict]:
    """Returns all temporary bans whose unban timestamp is in the past."""
    tempbans = load_tempbans()
    now = datetime.now(timezone.utc).timestamp()
    return [b for b in tempbans if b.get("unban_timestamp", 0) <= now]


# ==========================================
# FORUM CHANNEL & THREAD HELPERS
# ==========================================

async def setup_forum_threads(forum: discord.ForumChannel) -> int:
    """
    Ensures all 5 logging category threads exist in the forum channel.
    Returns the count of created threads.
    """
    created_count = 0
    existing_names = {t.name.lower() for t in forum.threads}

    try:
        async for t in forum.archived_threads(limit=50):
            existing_names.add(t.name.lower())
    except Exception:
        pass

    for key, cfg in FORUM_THREAD_CONFIG.items():
        name = cfg["name"]
        if name.lower() not in existing_names:
            intro_embed = discord.Embed(
                title=f"📋 {name} Feed",
                description=f"{cfg['desc']}\n\n*This thread was automatically created by {config.BOT_NAME} to organize logs.*",
                color=0xA240F7,
                timestamp=datetime.now(timezone.utc),
            )
            intro_embed.set_footer(text=f"{config.BOT_NAME} Logging System")

            create_kwargs = {
                "name": name,
                "embed": intro_embed,
                "reason": f"Auto-created {name} logging thread",
            }
            if forum.flags.require_tag and forum.available_tags:
                create_kwargs["applied_tags"] = [forum.available_tags[0]]

            try:
                await forum.create_thread(**create_kwargs)
                created_count += 1
                logger.info(f"Created forum log thread: {name} in {forum.name}")
            except Exception as e:
                logger.error(f"Failed to create initial forum thread {name}: {e}", exc_info=True)

    return created_count


async def _get_or_create_forum_thread(
    forum: discord.ForumChannel,
    thread_name: str,
    default_embed: discord.Embed | None = None,
    file: discord.File | None = None,
) -> tuple[discord.Thread | None, bool]:
    """
    Finds existing thread or creates it.
    Returns (thread, newly_created).
    """
    # 1. Check active threads in forum
    for thread in forum.threads:
        if thread.name.lower() == thread_name.lower():
            if thread.archived:
                try:
                    await thread.edit(archived=False)
                except Exception:
                    pass
            return thread, False

    # 2. Check archived threads
    try:
        async for thread in forum.archived_threads(limit=50):
            if thread.name.lower() == thread_name.lower():
                try:
                    await thread.edit(archived=False)
                except Exception:
                    pass
                return thread, False
    except Exception:
        pass

    # 3. Create new thread in forum
    intro = default_embed or discord.Embed(
        title=f"📋 {thread_name} Feed",
        description=f"Automated logging thread for {thread_name}.",
        color=0xA240F7,
        timestamp=datetime.now(timezone.utc),
    )
    create_kwargs = {
        "name": thread_name,
        "embed": intro,
        "reason": f"Auto-created {thread_name} thread for Miso logging",
    }
    if file:
        create_kwargs["file"] = file
    if forum.flags.require_tag and forum.available_tags:
        create_kwargs["applied_tags"] = [forum.available_tags[0]]

    try:
        thread_with_msg = await forum.create_thread(**create_kwargs)
        return thread_with_msg.thread, True
    except Exception as e:
        logger.error(f"Failed to create forum thread {thread_name} in {forum.name}: {e}", exc_info=True)
        return None, False


async def send_mod_log(
    guild: discord.Guild,
    embed: discord.Embed | None = None,
    log_type: str = "moderation",
    *,
    file: discord.File | None = None,
    view: discord.ui.LayoutView | None = None,
    content: str | None = None,
) -> None:
    """
    Sends a log entry to the configured channel.
    Supports standard Text Channels and Forum Channels (with threads).
    Supports discord.Embed, discord.File, and Components V2 (LayoutView).
    """
    channel_id = get_mod_log_channel_id(guild.id)
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(channel_id)
        except Exception as e:
            logger.warning(f"Could not fetch log channel {channel_id} in {guild.name}: {e}")
            return

    send_kwargs = {}
    if content:
        send_kwargs["content"] = content
    if embed:
        send_kwargs["embed"] = embed
    if file:
        send_kwargs["file"] = file
    if view:
        send_kwargs["view"] = view

    try:
        if isinstance(channel, discord.ForumChannel):
            cfg = FORUM_THREAD_CONFIG.get(log_type, {"name": f"📋・{log_type}"})
            thread_name = cfg["name"]
            thread, newly_created = await _get_or_create_forum_thread(channel, thread_name, embed, file)
            if thread:
                if newly_created:
                    # embed + file were already sent as the starter post by create_thread.
                    # Only send a follow-up if there's a view to attach.
                    if view:
                        await thread.send(view=view)
                else:
                    await thread.send(**send_kwargs)
        elif isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
            permissions = channel.permissions_for(guild.me)
            if permissions.send_messages and permissions.embed_links:
                await channel.send(**send_kwargs)
    except Exception as e:
        logger.error(f"Failed to send mod log to channel {channel_id} in {guild.name}: {e}", exc_info=True)
