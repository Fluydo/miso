"""
functions/welcome.py
Configuration persistence for Welcome & Leave greeting channels.
"""

import json
import logging
from typing import Optional

import config

logger = logging.getLogger("miso.functions.welcome")
_welcome_data: Optional[dict] = None


def load_welcome_config() -> dict:
    global _welcome_data
    if _welcome_data is not None:
        return _welcome_data

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.WELCOME_FILE.exists():
        _welcome_data = {}
        save_welcome_config(_welcome_data)
        return _welcome_data

    try:
        with open(config.WELCOME_FILE, "r", encoding="utf-8") as f:
            _welcome_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load welcome.json: {e}")
        _welcome_data = {}

    return _welcome_data


def save_welcome_config(data: dict) -> None:
    global _welcome_data
    _welcome_data = data
    try:
        with open(config.WELCOME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error(f"Failed to save welcome.json: {e}")


def _guild_welcome(data: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {"welcome_channel_id": None, "leave_channel_id": None}
    return data[gid]


def set_welcome_channel(guild_id: int, channel_id: Optional[int]) -> None:
    data = load_welcome_config()
    g = _guild_welcome(data, guild_id)
    g["welcome_channel_id"] = channel_id
    save_welcome_config(data)


def set_leave_channel(guild_id: int, channel_id: Optional[int]) -> None:
    data = load_welcome_config()
    g = _guild_welcome(data, guild_id)
    g["leave_channel_id"] = channel_id
    save_welcome_config(data)


def get_welcome_channels(guild_id: int) -> tuple[Optional[int], Optional[int]]:
    data = load_welcome_config()
    g = _guild_welcome(data, guild_id)
    return g.get("welcome_channel_id"), g.get("leave_channel_id")
