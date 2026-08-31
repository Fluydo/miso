"""
functions/economy.py
Pure data-access layer for the Miso Economy & Minigames System.
Persists data to data/economy.json.
"""

import json
import logging
from datetime import datetime, timezone, timedelta

import config

logger = logging.getLogger("miso.economy")

DEFAULT_STARTING_BALANCE: int = 250
DAILY_REWARD_AMOUNT: int = 150


def _ensure_economy_file() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.ECONOMY_FILE.exists():
        with open(config.ECONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load_economy() -> dict[str, dict]:
    """Loads all economy user records from disk."""
    _ensure_economy_file()
    try:
        with open(config.ECONOMY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading economy file: {e}. Resetting.")
        return {}


def save_economy(data: dict[str, dict]) -> None:
    """Saves economy user records to disk."""
    _ensure_economy_file()
    try:
        with open(config.ECONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Error saving economy file: {e}")


def _get_user_record(data: dict[str, dict], user_id: int) -> dict:
    """Gets or initializes a user's economy record."""
    key = str(user_id)
    if key not in data:
        data[key] = {
            "wallet": DEFAULT_STARTING_BALANCE,
            "bank": 0,
            "last_daily": None,
            "streak": 0,
            "games_played": 0,
            "games_won": 0,
            "total_profit": 0,
        }
    return data[key]


def get_balance(user_id: int) -> int:
    """Retrieves a user's wallet balance."""
    data = load_economy()
    return _get_user_record(data, user_id).get("wallet", DEFAULT_STARTING_BALANCE)


def add_balance(user_id: int, amount: int) -> int:
    """Adds coins to a user's wallet and returns the new balance."""
    if amount <= 0:
        return get_balance(user_id)
    data = load_economy()
    record = _get_user_record(data, user_id)
    record["wallet"] = record.get("wallet", 0) + amount
    save_economy(data)
    return record["wallet"]


def remove_balance(user_id: int, amount: int) -> bool:
    """Safely removes coins from a user's wallet. Returns True on success, False if insufficient."""
    if amount <= 0:
        return True
    data = load_economy()
    record = _get_user_record(data, user_id)
    current = record.get("wallet", 0)
    if current < amount:
        return False
    record["wallet"] = current - amount
    save_economy(data)
    return True


def record_game_result(user_id: int, won: bool, profit_or_loss: int) -> None:
    """Records statistics for minigame wins, losses, and net profits."""
    data = load_economy()
    record = _get_user_record(data, user_id)
    record["games_played"] = record.get("games_played", 0) + 1
    if won:
        record["games_won"] = record.get("games_won", 0) + 1
    record["total_profit"] = record.get("total_profit", 0) + profit_or_loss
    save_economy(data)


def claim_daily(user_id: int) -> tuple[bool, int, str | None]:
    """
    Attempts to claim daily reward.
    Returns (success, amount_awarded, time_remaining_or_message).
    """
    data = load_economy()
    record = _get_user_record(data, user_id)
    now = datetime.now(timezone.utc)
    last_daily_raw = record.get("last_daily")

    if last_daily_raw:
        try:
            last_dt = datetime.fromisoformat(last_daily_raw)
            diff = now - last_dt
            if diff < timedelta(hours=24):
                remaining = timedelta(hours=24) - diff
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours}h {minutes}m {seconds}s"
                return False, 0, time_str
            # Check streak bonus (if claimed within 48h)
            if diff < timedelta(hours=48):
                record["streak"] = record.get("streak", 0) + 1
            else:
                record["streak"] = 1
        except Exception:
            record["streak"] = 1
    else:
        record["streak"] = 1

    streak = record.get("streak", 1)
    streak_bonus = min((streak - 1) * 20, 200)
    total_reward = DAILY_REWARD_AMOUNT + streak_bonus

    record["wallet"] = record.get("wallet", 0) + total_reward
    record["last_daily"] = now.isoformat()
    save_economy(data)
    return True, total_reward, f"Streak: **{streak}** days (+{streak_bonus} bonus)"


def transfer_coins(sender_id: int, receiver_id: int, amount: int) -> tuple[bool, str]:
    """Transfers coins between two users."""
    if sender_id == receiver_id:
        return False, "You cannot transfer coins to yourself."
    if amount <= 0:
        return False, "Transfer amount must be at least 1 coin."

    data = load_economy()
    sender = _get_user_record(data, sender_id)
    receiver = _get_user_record(data, receiver_id)

    if sender.get("wallet", 0) < amount:
        return False, "You do not have enough coins in your wallet."

    sender["wallet"] -= amount
    receiver["wallet"] = receiver.get("wallet", 0) + amount
    save_economy(data)
    return True, "Success"


def get_rich_leaderboard(limit: int = 10) -> list[dict]:
    """Returns top users sorted by wallet balance."""
    data = load_economy()
    users = []
    for uid_str, record in data.items():
        if uid_str.isdigit():
            users.append({
                "user_id": int(uid_str),
                "wallet": record.get("wallet", 0),
                "games_won": record.get("games_won", 0),
            })
    users.sort(key=lambda x: x["wallet"], reverse=True)
    return users[:limit]
