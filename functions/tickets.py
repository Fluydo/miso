"""
functions/tickets.py
Data layer for Miso Bot's Ticket System.
Stores panel configurations and active ticket metadata in data/tickets.json.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import config

logger = logging.getLogger("miso.tickets")


def _ensure_tickets_file() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.TICKETS_FILE.exists():
        with open(config.TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load_tickets() -> dict[str, dict]:
    """Loads all ticket data from disk."""
    _ensure_tickets_file()
    try:
        with open(config.TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error reading tickets file: {e}. Resetting.")
        return {}


def save_tickets(data: dict[str, dict]) -> None:
    """Saves ticket data to disk."""
    _ensure_tickets_file()
    try:
        with open(config.TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Error saving tickets file: {e}")


def get_guild_ticket_config(guild_id: int) -> dict:
    """Retrieves or initializes ticket settings for a guild."""
    data = load_tickets()
    key = str(guild_id)
    if key not in data:
        data[key] = {
            "category_id": None,
            "ticket_counter": 0,
            "active_tickets": {},  # channel_id: {user_id, type, created_at, claimed_by}
        }
        save_tickets(data)
    return data[key]


def set_ticket_category(guild_id: int, category_id: int | None) -> None:
    """Sets the Discord category ID under which ticket channels are created."""
    data = load_tickets()
    key = str(guild_id)
    if key not in data:
        data[key] = {"category_id": category_id, "ticket_counter": 0, "active_tickets": {}}
    else:
        data[key]["category_id"] = category_id
    save_tickets(data)


def register_new_ticket(
    guild_id: int,
    channel_id: int,
    user_id: int,
    ticket_type: str,
) -> int:
    """Registers a newly opened ticket and returns its incremented ticket number."""
    data = load_tickets()
    key = str(guild_id)
    if key not in data:
        data[key] = {"category_id": None, "ticket_counter": 0, "active_tickets": {}}

    data[key]["ticket_counter"] = data[key].get("ticket_counter", 0) + 1
    ticket_num = data[key]["ticket_counter"]

    data[key].setdefault("active_tickets", {})[str(channel_id)] = {
        "ticket_num": ticket_num,
        "user_id": user_id,
        "type": ticket_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claimed_by": None,
    }
    save_tickets(data)
    return ticket_num


def get_ticket_info(guild_id: int, channel_id: int) -> Optional[dict]:
    """Retrieves metadata for an active ticket channel."""
    data = load_tickets()
    guild_data = data.get(str(guild_id), {})
    return guild_data.get("active_tickets", {}).get(str(channel_id))


def claim_ticket(guild_id: int, channel_id: int, staff_id: int) -> bool:
    """Marks a ticket channel as claimed by a staff member."""
    data = load_tickets()
    key = str(guild_id)
    ch_key = str(channel_id)
    if key in data and ch_key in data[key].get("active_tickets", {}):
        data[key]["active_tickets"][ch_key]["claimed_by"] = staff_id
        save_tickets(data)
        return True
    return False


def remove_ticket_record(guild_id: int, channel_id: int) -> Optional[dict]:
    """Removes a ticket channel from active tickets."""
    data = load_tickets()
    key = str(guild_id)
    ch_key = str(channel_id)
    if key in data and ch_key in data[key].get("active_tickets", {}):
        removed = data[key]["active_tickets"].pop(ch_key)
        save_tickets(data)
        return removed
    return None
