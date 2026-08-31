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
) -> None:
    data = load_giveaways()
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

    if entries:
        chosen = random.sample(entries, min(len(entries), winners_count))
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
