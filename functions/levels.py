"""
functions/levels.py
Leveling, XP calculations, and data persistence for Miso Bot.
"""

import json
import logging
import math
import time
from typing import Optional

import config

logger = logging.getLogger("miso.functions.levels")

_levels_data: Optional[dict] = None
_xp_cooldowns: dict[tuple[int, int], float] = {}  # (guild_id, user_id) -> last_xp_timestamp

# Level Milestones and Role Config
LEVEL_MILESTONES = [5, 10, 15, 20, 25]
MILESTONE_ROLE_NAMES = {
    5: "Level 5 🥉",
    10: "Level 10 🥈",
    15: "Level 15 🥇",
    20: "Level 20 💎",
    25: "Level 25 👑",
}
MILESTONE_ROLE_COLORS = {
    5: 0xcd7f32,   # Bronze
    10: 0xc0c0c0,  # Silver
    15: 0xffd700,  # Gold
    20: 0x3d8cff,  # Diamond Blue
    25: 0xa240f7,  # Purple Crown
}


def load_levels() -> dict:
    global _levels_data
    if _levels_data is not None:
        return _levels_data

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.LEVELS_FILE.exists():
        _levels_data = {}
        save_levels(_levels_data)
        return _levels_data

    try:
        with open(config.LEVELS_FILE, "r", encoding="utf-8") as f:
            _levels_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load levels.json: {e}")
        _levels_data = {}

    return _levels_data


def save_levels(data: dict) -> None:
    global _levels_data
    _levels_data = data
    try:
        with open(config.LEVELS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error(f"Failed to save levels.json: {e}")


def _guild_levels(data: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    return data[gid]


def xp_for_level(level: int) -> int:
    """Returns the total XP required to complete a given level."""
    return 100 * (level ** 2) + 50 * level


def add_xp(guild_id: int, user_id: int, xp_to_add: int = 15) -> tuple[int, int, bool]:
    """
    Adds XP with a 60-second spam cooldown.
    Returns (current_level, current_xp, leveled_up_boolean).
    """
    now = time.time()
    last_time = _xp_cooldowns.get((guild_id, user_id), 0.0)
    if now - last_time < 60.0:
        data = load_levels()
        g_data = _guild_levels(data, guild_id)
        u_record = g_data.get(str(user_id), {"xp": 0, "level": 0})
        return u_record["level"], u_record["xp"], False

    _xp_cooldowns[(guild_id, user_id)] = now

    data = load_levels()
    g_data = _guild_levels(data, guild_id)
    uid = str(user_id)

    if uid not in g_data:
        g_data[uid] = {"xp": 0, "level": 0}

    record = g_data[uid]
    record["xp"] += xp_to_add

    req = xp_for_level(record["level"] + 1)
    leveled_up = False

    while record["xp"] >= req:
        record["level"] += 1
        leveled_up = True
        req = xp_for_level(record["level"] + 1)

    save_levels(data)
    return record["level"], record["xp"], leveled_up


def get_user_level(guild_id: int, user_id: int) -> tuple[int, int, int, int]:
    """
    Returns (level, current_xp, next_level_xp, rank_position).
    """
    data = load_levels()
    g_data = _guild_levels(data, guild_id)
    uid = str(user_id)
    record = g_data.get(uid, {"xp": 0, "level": 0})

    level = record["level"]
    xp = record["xp"]
    next_req = xp_for_level(level + 1)

    sorted_users = sorted(g_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
    rank_pos = 1
    for i, (u, _) in enumerate(sorted_users):
        if u == uid:
            rank_pos = i + 1
            break

    return level, xp, next_req, rank_pos


def get_levels_leaderboard(guild_id: int, limit: int = 50) -> list[dict]:
    data = load_levels()
    g_data = _guild_levels(data, guild_id)

    sorted_users = sorted(g_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
    results = []
    for uid, r in sorted_users[:limit]:
        results.append({
            "user_id": int(uid),
            "level": r["level"],
            "xp": r["xp"],
        })
    return results


def admin_set_level(guild_id: int, user_id: int, new_level: int) -> tuple[int, int, int]:
    """Set a user's level directly. Returns (level, xp, next_req)."""
    new_level = max(0, new_level)
    data = load_levels()
    g_data = _guild_levels(data, guild_id)
    uid = str(user_id)
    record = g_data.setdefault(uid, {"xp": 0, "level": 0})
    record["level"] = new_level
    # Reset XP to start of that level
    record["xp"] = 0
    save_levels(data)
    return record["level"], record["xp"], xp_for_level(new_level + 1)


def admin_give_level(guild_id: int, user_id: int, amount: int) -> tuple[int, int, int]:
    """Give (or remove with negative) levels. Returns (level, xp, next_req)."""
    data = load_levels()
    g_data = _guild_levels(data, guild_id)
    uid = str(user_id)
    record = g_data.setdefault(uid, {"xp": 0, "level": 0})
    record["level"] = max(0, record["level"] + amount)
    save_levels(data)
    return record["level"], record["xp"], xp_for_level(record["level"] + 1)


def admin_set_xp(guild_id: int, user_id: int, new_xp: int) -> tuple[int, int, int]:
    """Set a user's XP directly, recalculating level. Returns (level, xp, next_req)."""
    new_xp = max(0, new_xp)
    data = load_levels()
    g_data = _guild_levels(data, guild_id)
    uid = str(user_id)
    record = g_data.setdefault(uid, {"xp": 0, "level": 0})
    record["xp"] = new_xp
    # Recalculate level from XP
    level = 0
    while new_xp >= xp_for_level(level + 1):
        level += 1
    record["level"] = level
    save_levels(data)
    return record["level"], record["xp"], xp_for_level(level + 1)


def admin_give_xp(guild_id: int, user_id: int, amount: int) -> tuple[int, int, int]:
    """Give (or remove with negative) XP, recalculating level. Returns (level, xp, next_req)."""
    data = load_levels()
    g_data = _guild_levels(data, guild_id)
    uid = str(user_id)
    record = g_data.setdefault(uid, {"xp": 0, "level": 0})
    record["xp"] = max(0, record["xp"] + amount)
    # Recalculate level
    xp = record["xp"]
    level = 0
    while xp >= xp_for_level(level + 1):
        level += 1
    record["level"] = level
    save_levels(data)
    return record["level"], record["xp"], xp_for_level(level + 1)

