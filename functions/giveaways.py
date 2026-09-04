"""
functions/giveaways.py
Giveaways data storage and winner selection helpers for Miso Bot.
"""

import json
import logging
import random
import time
from typing import Optional

import config

logger = logging.getLogger("miso.functions.giveaways")
_giveaways_data: Optional[dict] = None


def load_giveaways() -> dict:
    global _giveaways_data
    if _giveaways_data is not None:
        return _giveaways_data

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.GIVEAWAYS_FILE.exists():
        _giveaways_data = {}
        save_giveaways(_giveaways_data)
        return _giveaways_data

    try:
        with open(config.GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
            _giveaways_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load giveaways.json: {e}")
        _giveaways_data = {}

    return _giveaways_data


def save_giveaways(data: dict) -> None:
    global _giveaways_data
    _giveaways_data = data
    try:
        with open(config.GIVEAWAYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error(f"Failed to save giveaways.json: {e}")


def create_giveaway(
    guild_id: int,
    channel_id: int,
    message_id: int,
    prize: str,
    winners_count: int,
    end_timestamp: float,
    host_id: int,
    min_invites: Optional[int] = None,
    required_roles: Optional[list[int]] = None,
) -> None:
    data = load_giveaways()
    
    # Build requirements dict
    requirements = {}
    if min_invites is not None and min_invites > 0:
        requirements["min_invites"] = min_invites
    if required_roles:
        requirements["required_roles"] = [str(r) for r in required_roles]
    
    data[str(message_id)] = {
        "guild_id": guild_id,
        "channel_id": channel_id,
        "message_id": message_id,
        "prize": prize,
        "winners_count": winners_count,
        "end_timestamp": end_timestamp,
        "host_id": host_id,
        "entries": [],
        "ended": False,
        "winners": [],
        "requirements": requirements,
        "winner_id": None,
        "redeemed": False,
        "redemption_expires": None,
        "ticket_id": None,
        "dm_sent": False,
    }
    save_giveaways(data)


def add_entry(message_id: int, user_id: int) -> tuple[bool, int]:
    """Adds a user to a giveaway. Returns (is_added, total_entries). If already entered, removes entry (toggle)."""
    data = load_giveaways()
    mid = str(message_id)
    if mid not in data or data[mid].get("ended"):
        return False, 0

    entries = data[mid].setdefault("entries", [])
    if user_id in entries:
        entries.remove(user_id)
        save_giveaways(data)
        return False, len(entries)

    entries.append(user_id)
    save_giveaways(data)
    return True, len(entries)


def end_giveaway(message_id: int) -> Optional[dict]:
    data = load_giveaways()
    mid = str(message_id)
    if mid not in data or data[mid].get("ended"):
        return None

    record = data[mid]
    record["ended"] = True
    entries = record.get("entries", [])
    winners_count = record.get("winners_count", 1)
    requirements = record.get("requirements", {})

    # Filter entries by requirements if any exist
    valid_entries = entries
    if requirements:
        # We'll mark invalid entries for filtering
        # Note: This is a simple check - the actual validation happened on entry
        # But users might have lost invites/roles after entering
        valid_entries = entries  # For now, trust the entry validation
        # TODO: Add re-validation logic if needed

    if valid_entries:
        chosen = random.sample(valid_entries, min(len(valid_entries), winners_count))
    else:
        chosen = []

    record["winners"] = chosen
    save_giveaways(data)
    return record


def reroll_giveaway(message_id: int) -> tuple[Optional[int], str]:
    data = load_giveaways()
    mid = str(message_id)
    if mid not in data:
        return None, "Giveaway not found."

    record = data[mid]
    entries = record.get("entries", [])
    if not entries:
        return None, "No entries in this giveaway."

    new_winner = random.choice(entries)
    record["winners"] = [new_winner]
    save_giveaways(data)
    return new_winner, record.get("prize", "Prize")


def reroll_giveaway_redemption(message_id: int) -> tuple[Optional[int], str, int]:
    """
    Reroll a giveaway with redemption system.
    Returns (new_winner_id, prize, expiry_timestamp) or (None, error_msg, 0)
    """
    data = load_giveaways()
    mid = str(message_id)
    if mid not in data:
        return None, "Giveaway not found.", 0

    record = data[mid]
    entries = record.get("entries", [])
    
    # Remove current winner from pool if they didn't redeem
    current_winner = record.get("winner_id")
    available_entries = [e for e in entries if e != current_winner] if current_winner else entries
    
    if not available_entries:
        return None, "No more entries available for reroll.", 0

    new_winner = random.choice(available_entries)
    expires_ts = int(time.time() + 86400)  # 24 hours from now
    
    record["winners"] = [new_winner]
    record["winner_id"] = new_winner
    record["redeemed"] = False
    record["redeemed_at"] = None
    record["redemption_expires"] = expires_ts
    record["ticket_id"] = None
    record["dm_sent"] = False
    
    save_giveaways(data)
    return new_winner, record.get("prize", "Prize"), expires_ts
