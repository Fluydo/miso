"""
functions/antinuke.py
Anti-Nuke protection data and rate-limiting tracker.
"""

import json
import logging
import time
from typing import Optional

import config

logger = logging.getLogger("miso.functions.antinuke")
_antinuke_data: Optional[dict] = None

# (guild_id, user_id, action_type) -> list of float timestamps
_action_history: dict[tuple[int, int, str], list[float]] = {}


def load_antinuke_config() -> dict:
    global _antinuke_data
    if _antinuke_data is not None:
        return _antinuke_data

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.ANTINUKE_FILE.exists():
        _antinuke_data = {}
        save_antinuke_config(_antinuke_data)
        return _antinuke_data

    try:
        with open(config.ANTINUKE_FILE, "r", encoding="utf-8") as f:
            _antinuke_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load antinuke.json: {e}")
        _antinuke_data = {}

    return _antinuke_data


def save_antinuke_config(data: dict) -> None:
    global _antinuke_data
    _antinuke_data = data
    try:
        with open(config.ANTINUKE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error(f"Failed to save antinuke.json: {e}")


def _guild_antinuke(data: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {
            "enabled": True,
            "threshold": 3,   # actions in 10s window
            "window_seconds": 10,
        }
    return data[gid]


def is_antinuke_enabled(guild_id: int) -> bool:
    data = load_antinuke_config()
    g = _guild_antinuke(data, guild_id)
    return g.get("enabled", True)


def set_antinuke_enabled(guild_id: int, enabled: bool) -> None:
    data = load_antinuke_config()
    g = _guild_antinuke(data, guild_id)
    g["enabled"] = enabled
    save_antinuke_config(data)


def set_antinuke_threshold(guild_id: int, threshold: int) -> None:
    data = load_antinuke_config()
    g = _guild_antinuke(data, guild_id)
    g["threshold"] = max(2, threshold)
    save_antinuke_config(data)


def get_antinuke_settings(guild_id: int) -> dict:
    data = load_antinuke_config()
    return _guild_antinuke(data, guild_id)


def record_and_check_violation(guild_id: int, user_id: int, action_type: str) -> tuple[bool, int, int]:
    """
    Records an administrative action and checks if the rate limit is violated.
    Returns (is_violated, current_action_count, threshold).
    """
    if not is_antinuke_enabled(guild_id):
        return False, 0, 0

    settings = get_antinuke_settings(guild_id)
    threshold = settings.get("threshold", 3)
    window = settings.get("window_seconds", 10)

    now = time.time()
    key = (guild_id, user_id, action_type)
    if key not in _action_history:
        _action_history[key] = []

    # Clean old timestamps
    _action_history[key] = [t for t in _action_history[key] if now - t <= window]
    _action_history[key].append(now)

    count = len(_action_history[key])
    if count >= threshold:
        # Reset tracker to avoid repeat immediate triggers
        _action_history[key] = []
        return True, count, threshold

    return False, count, threshold
