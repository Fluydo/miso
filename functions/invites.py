"""
functions/invites.py
Pure data-access layer for the invite tracking system.
No discord.py imports — all I/O is synchronous JSON, matching the style of functions/moderation.py.
"""

import json
import logging
from datetime import datetime, timezone

import config

logger = logging.getLogger("miso.invite_functions")


# ==========================================
# FILE HELPERS
# ==========================================

def _ensure_invites_file() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.INVITES_FILE.exists():
        with open(config.INVITES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load_invites() -> dict:
    _ensure_invites_file()
    try:
        with open(config.INVITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading invites file: {e}. Resetting.")
        return {}


def save_invites(data: dict) -> None:
    _ensure_invites_file()
    try:
        with open(config.INVITES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Error saving invites file: {e}")


# ==========================================
# GUILD-LEVEL ACCESSORS
# ==========================================

def _guild_data(data: dict, guild_id: int) -> dict:
    """Returns the mutable guild sub-dict, creating it if absent."""
    key = str(guild_id)
    if key not in data:
        data[key] = {"invites": {}, "members": {}}
    if "invites" not in data[key]:
        data[key]["invites"] = {}
    if "members" not in data[key]:
        data[key]["members"] = {}
    return data[key]


def get_guild_invites(guild_id: int) -> dict:
    """Returns {code: invite_record} for a guild."""
    data = load_invites()
    return _guild_data(data, guild_id)["invites"]


def get_guild_members(guild_id: int) -> dict:
    """Returns {member_id: member_record} for a guild."""
    data = load_invites()
    return _guild_data(data, guild_id)["members"]


# ==========================================
# INVITE RECORD MANAGEMENT
# ==========================================

def upsert_invite(
    guild_id: int,
    code: str,
    inviter_id: int | None,
    uses: int,
    max_uses: int = 0,
    max_age: int = 0,
) -> None:
    """Insert or update an invite record."""
    data = load_invites()
    guild = _guild_data(data, guild_id)
    guild["invites"][code] = {
        "inviter_id": inviter_id,
        "uses": uses,
        "max_uses": max_uses,
        "max_age": max_age,
        "created_at": guild["invites"].get(code, {}).get(
            "created_at", datetime.now(timezone.utc).isoformat()
        ),
    }
    save_invites(data)


def delete_invite(guild_id: int, code: str) -> None:
    """Remove an invite record (e.g. when it is deleted/expired)."""
    data = load_invites()
    guild = _guild_data(data, guild_id)
    guild["invites"].pop(code, None)
    save_invites(data)


def bulk_sync_invites(guild_id: int, invite_snapshot: dict[str, dict]) -> None:
    """
    Replace the stored invite cache for a guild with a fresh snapshot.
    invite_snapshot: { code: {inviter_id, uses, max_uses, max_age} }
    """
    data = load_invites()
    guild = _guild_data(data, guild_id)
    existing = guild["invites"]

    for code, info in invite_snapshot.items():
        existing[code] = {
            "inviter_id": info.get("inviter_id"),
            "uses": info.get("uses", 0),
            "max_uses": info.get("max_uses", 0),
            "max_age": info.get("max_age", 0),
            "created_at": existing.get(code, {}).get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
        }

    # Remove codes that no longer exist in Discord
    stored_codes = set(existing.keys())
    live_codes = set(invite_snapshot.keys())
    for dead_code in stored_codes - live_codes:
        existing.pop(dead_code, None)

    guild["invites"] = existing
    save_invites(data)


# ==========================================
# MEMBER JOIN / LEAVE TRACKING
# ==========================================

def record_join(
    guild_id: int,
    member_id: int,
    inviter_id: int | None,
    code: str | None,
) -> None:
    """
    Record that a member joined via a specific invite.
    Re-joins overwrite the previous record (prevents duplicate counting).
    """
    data = load_invites()
    guild = _guild_data(data, guild_id)
    guild["members"][str(member_id)] = {
        "inviter_id": inviter_id,
        "invite_code": code,
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    save_invites(data)


def record_leave(guild_id: int, member_id: int) -> int | None:
    """
    Mark a member's join record as 'left'.
    Returns the inviter_id so the cog can update the log, or None if unknown.
    """
    data = load_invites()
    guild = _guild_data(data, guild_id)
    key = str(member_id)
    record = guild["members"].get(key)
    if record:
        record["status"] = "left"
        save_invites(data)
        return record.get("inviter_id")
    return None


# ==========================================
# STATISTICS
# ==========================================

def get_invite_stats(guild_id: int, user_id: int) -> dict:
    """
    Returns invite stats for a user in a guild.
    {
        "total":  int,   # all members ever attributed to this inviter
        "active": int,   # members still in the server
        "left":   int,   # members who left
    }
    """
    members = get_guild_members(guild_id)
    total = active = left = 0

    for record in members.values():
        if record.get("inviter_id") != user_id:
            continue
        total += 1
        status = record.get("status", "active")
        if status == "active":
            active += 1
        elif status == "left":
            left += 1

    return {"total": total, "active": active, "left": left}


def get_leaderboard(guild_id: int, limit: int = 10) -> list[dict]:
    """
    Returns a sorted list of top inviters by active member count.
    Each entry: { "inviter_id": int, "total": int, "active": int, "left": int }
    """
    members = get_guild_members(guild_id)

    # Aggregate per inviter
    aggregated: dict[int, dict] = {}
    for record in members.values():
        inv_id = record.get("inviter_id")
        if inv_id is None:
            continue
        if inv_id not in aggregated:
            aggregated[inv_id] = {"inviter_id": inv_id, "total": 0, "active": 0, "left": 0}
        aggregated[inv_id]["total"] += 1
        status = record.get("status", "active")
        if status == "active":
            aggregated[inv_id]["active"] += 1
        elif status == "left":
            aggregated[inv_id]["left"] += 1

    # Sort by active desc, then total desc as tiebreaker
    sorted_entries = sorted(
        aggregated.values(),
        key=lambda e: (e["active"], e["total"]),
        reverse=True,
    )
    return sorted_entries[:limit]
