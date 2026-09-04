"""
functions/verification.py
Data storage and settings for the Member Verification System.
"""

import json
import logging
from typing import Optional

import config

logger = logging.getLogger("miso.functions.verification")
_verification_data: Optional[dict] = None


def load_verification_config() -> dict:
    global _verification_data
    if _verification_data is not None:
        return _verification_data

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.VERIFICATION_FILE.exists():
        _verification_data = {}
        save_verification_config(_verification_data)
        return _verification_data

    try:
        with open(config.VERIFICATION_FILE, "r", encoding="utf-8") as f:
            _verification_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load verification.json: {e}")
        _verification_data = {}

    return _verification_data


def save_verification_config(data: dict) -> None:
    global _verification_data
    _verification_data = data
    try:
        with open(config.VERIFICATION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error(f"Failed to save verification.json: {e}")


def _guild_verify(data: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {
            "verify_channel_id": None,
            "verified_role_id": None,
            "exception_channel_ids": [],
            "blacklisted_channel_ids": [],  # Channels verified users CAN'T see
            "blacklisted_category_ids": [],  # Categories verified users CAN'T see
        }
    # Add blacklist keys if missing (for existing configs)
    if "blacklisted_channel_ids" not in data[gid]:
        data[gid]["blacklisted_channel_ids"] = []
    if "blacklisted_category_ids" not in data[gid]:
        data[gid]["blacklisted_category_ids"] = []
    return data[gid]


def set_verification_setup(guild_id: int, channel_id: int, role_id: int) -> None:
    data = load_verification_config()
    g = _guild_verify(data, guild_id)
    g["verify_channel_id"] = channel_id
    g["verified_role_id"] = role_id
    save_verification_config(data)


def add_exception_channel(guild_id: int, channel_id: int) -> bool:
    data = load_verification_config()
    g = _guild_verify(data, guild_id)
    exceptions = g.setdefault("exception_channel_ids", [])
    if channel_id not in exceptions:
        exceptions.append(channel_id)
        save_verification_config(data)
        return True
    return False


def remove_exception_channel(guild_id: int, channel_id: int) -> bool:
    data = load_verification_config()
    g = _guild_verify(data, guild_id)
    exceptions = g.setdefault("exception_channel_ids", [])
    if channel_id in exceptions:
        exceptions.remove(channel_id)
        save_verification_config(data)
        return True
    return False


def get_verification_settings(guild_id: int) -> dict:
    data = load_verification_config()
    return _guild_verify(data, guild_id)


def add_blacklisted_channel(guild_id: int, channel_id: int) -> bool:
    """Add a channel that verified users should NOT be able to see."""
    data = load_verification_config()
    g = _guild_verify(data, guild_id)
    blacklist = g.setdefault("blacklisted_channel_ids", [])
    if channel_id not in blacklist:
        blacklist.append(channel_id)
        save_verification_config(data)
        return True
    return False


def remove_blacklisted_channel(guild_id: int, channel_id: int) -> bool:
    """Remove a channel from the blacklist."""
    data = load_verification_config()
    g = _guild_verify(data, guild_id)
    blacklist = g.setdefault("blacklisted_channel_ids", [])
    if channel_id in blacklist:
        blacklist.remove(channel_id)
        save_verification_config(data)
        return True
    return False


def add_blacklisted_category(guild_id: int, category_id: int) -> bool:
    """Add a category that verified users should NOT be able to see."""
    data = load_verification_config()
    g = _guild_verify(data, guild_id)
    blacklist = g.setdefault("blacklisted_category_ids", [])
    if category_id not in blacklist:
        blacklist.append(category_id)
        save_verification_config(data)
        return True
    return False


def remove_blacklisted_category(guild_id: int, category_id: int) -> bool:
    """Remove a category from the blacklist."""
    data = load_verification_config()
    g = _guild_verify(data, guild_id)
    blacklist = g.setdefault("blacklisted_category_ids", [])
    if category_id in blacklist:
        blacklist.remove(category_id)
        save_verification_config(data)
        return True
    return False
