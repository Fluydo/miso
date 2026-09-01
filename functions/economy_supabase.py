"""
functions/economy_supabase.py
Supabase-backed economy system - syncs with web dashboard.
"""

import logging
from typing import Optional
import httpx

import config

logger = logging.getLogger("miso.economy_supabase")

DEFAULT_STARTING_BALANCE: int = 250


async def get_balance(user_id: int) -> int:
    """Get user's coin balance from Supabase."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        logger.warning("Supabase not configured, returning default balance")
        return DEFAULT_STARTING_BALANCE

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/users?discord_id=eq.{user_id}&select=coins",
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                return data[0].get("coins", DEFAULT_STARTING_BALANCE)
        
        # User doesn't exist, return default
        return DEFAULT_STARTING_BALANCE


async def set_balance(user_id: int, amount: int) -> bool:
    """Set user's coin balance in Supabase."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    # Update existing user's balance
    payload = {"coins": max(0, amount)}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{config.SUPABASE_URL}/rest/v1/users?discord_id=eq.{user_id}",
            json=payload,
            headers=headers,
        )
        return resp.status_code in (200, 204)


async def add_balance(user_id: int, amount: int) -> int:
    """Add coins to user's balance and return new total."""
    if amount <= 0:
        return await get_balance(user_id)
    
    current = await get_balance(user_id)
    new_balance = current + amount
    await set_balance(user_id, new_balance)
    return new_balance


async def remove_balance(user_id: int, amount: int) -> bool:
    """Remove coins from user's balance. Returns False if insufficient funds."""
    if amount <= 0:
        return True
    
    current = await get_balance(user_id)
    if current < amount:
        return False
    
    new_balance = current - amount
    await set_balance(user_id, new_balance)
    return True


async def transfer_coins(sender_id: int, receiver_id: int, amount: int) -> tuple[bool, str]:
    """Transfer coins between users."""
    if sender_id == receiver_id:
        return False, "You cannot transfer coins to yourself."
    if amount <= 0:
        return False, "Transfer amount must be at least 1 coin."

    sender_balance = await get_balance(sender_id)
    if sender_balance < amount:
        return False, "You do not have enough coins."

    # Deduct from sender
    if not await remove_balance(sender_id, amount):
        return False, "Transaction failed."

    # Add to receiver
    await add_balance(receiver_id, amount)
    return True, "Success"


async def record_game_result(user_id: int, won: bool, profit_or_loss: int) -> None:
    """Record game statistics in game_history table."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    # Determine game name from context (you'll pass this as parameter)
    outcome = "win" if won else "loss"
    
    payload = {
        "discord_id": str(user_id),
        "game": "unknown",  # Should be passed as parameter
        "outcome": outcome,
        "delta": profit_or_loss,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{config.SUPABASE_URL}/rest/v1/game_history",
            json=payload,
            headers=headers,
        )


async def claim_daily(user_id: int) -> tuple[bool, int, str | None]:
    """
    Claim daily reward with streak tracking.
    Returns (success, amount_awarded, message).
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False, 0, "Supabase not configured"

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Get user data
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/users?discord_id=eq.{user_id}&select=last_daily,daily_streak,coins",
            headers=headers,
        )
        
        if resp.status_code != 200:
            return False, 0, "Failed to fetch user data"
        
        data = resp.json()
        if not data:
            # User doesn't exist yet
            user_data = {"coins": DEFAULT_STARTING_BALANCE, "last_daily": None, "daily_streak": 0}
        else:
            user_data = data[0]
        
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        last_daily = user_data.get("last_daily")
        
        if last_daily:
            last_dt = datetime.fromisoformat(last_daily.replace('Z', '+00:00'))
            diff = now - last_dt
            
            if diff < timedelta(hours=24):
                # Already claimed today
                remaining = timedelta(hours=24) - diff
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                time_str = f"{hours}h {minutes}m"
                return False, 0, f"Already claimed! Next in {time_str}"
            
            # Check streak
            if diff < timedelta(hours=48):
                new_streak = user_data.get("daily_streak", 0) + 1
            else:
                new_streak = 1
        else:
            new_streak = 1
        
        # Calculate reward
        base_reward = 150
        streak_bonus = min((new_streak - 1) * 20, 200)
        total_reward = base_reward + streak_bonus
        
        new_balance = user_data.get("coins", DEFAULT_STARTING_BALANCE) + total_reward
        
        # Update user
        update_payload = {
            "discord_id": str(user_id),
            "coins": new_balance,
            "daily_streak": new_streak,
            "last_daily": now.isoformat(),
        }
        
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "resolution=merge-duplicates"
        
        resp = await client.post(
            f"{config.SUPABASE_URL}/rest/v1/users",
            json=update_payload,
            headers=headers,
        )
        
        if resp.status_code in (200, 201):
            return True, total_reward, f"Streak: **{new_streak}** days (+{streak_bonus} bonus)"
        
        return False, 0, "Failed to update"


async def get_rich_leaderboard(limit: int = 10) -> list[dict]:
    """Get top users by coin balance from Supabase."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []

    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{config.SUPABASE_URL}/rest/v1/users?select=discord_id,coins,username,avatar&order=coins.desc&limit={limit}",
            headers=headers,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "user_id": int(u.get("discord_id", 0)),
                    "wallet": u.get("coins", 0),
                    "username": u.get("username", "Unknown"),
                    "avatar": u.get("avatar"),
                }
                for u in data
            ]
        
        return []
