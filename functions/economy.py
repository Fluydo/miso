"""
functions/economy.py
Server economy system with coins, transactions, and shop.
"""

import logging
from typing import Optional
import config

logger = logging.getLogger("miso.functions.economy")


async def get_economy_settings(guild_id: int) -> dict:
    """Get economy settings for a guild."""
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {
            'enabled': True,
            'currency_name': 'coins',
            'currency_symbol': '🪙',
            'daily_reward': 100,
            'message_reward_min': 5,
            'message_reward_max': 15,
            'voice_reward_per_minute': 3
        }
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('economy_settings').select('*').eq('guild_id', str(guild_id)).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {
            'enabled': True,
            'currency_name': 'coins',
            'currency_symbol': '🪙',
            'daily_reward': 100,
            'message_reward_min': 5,
            'message_reward_max': 15,
            'voice_reward_per_minute': 3
        }
    except Exception as e:
        logger.error(f"Failed to fetch economy settings: {e}")
        return {'enabled': True, 'currency_name': 'coins', 'currency_symbol': '🪙'}


async def get_balance(guild_id: int, user_id: int) -> dict:
    """
    Get user's balance.
    
    Returns:
        dict with keys: coins, bank, total_earned, total_spent
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'coins': 0, 'bank': 0, 'total_earned': 0, 'total_spent': 0}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('user_economy').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {'coins': 0, 'bank': 0, 'total_earned': 0, 'total_spent': 0}
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        return {'coins': 0, 'bank': 0, 'total_earned': 0, 'total_spent': 0}


async def add_coins(guild_id: int, user_id: int, amount: int, reason: str = 'earned') -> bool:
    """
    Add coins to user's wallet.
    
    Args:
        guild_id: Guild ID
        user_id: User ID
        amount: Amount to add (can be negative)
        reason: Transaction reason
    
    Returns:
        True if successful
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Get current balance
        response = supabase.table('user_economy').select('*').eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        if response.data and len(response.data) > 0:
            current = response.data[0]
            new_coins = current['coins'] + amount
            new_earned = current['total_earned'] + max(0, amount)
            new_spent = current['total_spent'] + max(0, -amount)
            
            supabase.table('user_economy').update({
                'coins': max(0, new_coins),
                'total_earned': new_earned,
                'total_spent': new_spent
            }).eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        else:
            # Create new entry
            supabase.table('user_economy').insert({
                'guild_id': str(guild_id),
                'user_id': str(user_id),
                'coins': max(0, amount),
                'bank': 0,
                'total_earned': max(0, amount),
                'total_spent': 0
            }).execute()
        
        # Log transaction
        supabase.table('economy_transactions').insert({
            'guild_id': str(guild_id),
            'user_id': str(user_id),
            'amount': amount,
            'transaction_type': 'earn' if amount > 0 else 'spend',
            'description': reason
        }).execute()
        
        return True
    except Exception as e:
        logger.error(f"Failed to add coins: {e}", exc_info=True)
        return False


async def transfer_coins(guild_id: int, from_user_id: int, to_user_id: int, amount: int) -> dict:
    """
    Transfer coins between users.
    
    Returns:
        dict with keys: success, message
    """
    if amount <= 0:
        return {'success': False, 'message': 'Amount must be positive'}
    
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'Economy system not available'}
    
    try:
        # Get sender balance
        sender_balance = await get_balance(guild_id, from_user_id)
        
        if sender_balance['coins'] < amount:
            return {'success': False, 'message': f'Insufficient funds. You have {sender_balance["coins"]} coins.'}
        
        # Deduct from sender
        await add_coins(guild_id, from_user_id, -amount, f'transferred to user {to_user_id}')
        
        # Add to recipient
        await add_coins(guild_id, to_user_id, amount, f'received from user {from_user_id}')
        
        return {'success': True, 'message': f'Successfully transferred {amount} coins!'}
    except Exception as e:
        logger.error(f"Failed to transfer coins: {e}")
        return {'success': False, 'message': f'Transfer failed: {str(e)}'}


async def deposit_coins(guild_id: int, user_id: int, amount: int) -> dict:
    """
    Deposit coins from wallet to bank.
    
    Returns:
        dict with keys: success, message
    """
    if amount <= 0:
        return {'success': False, 'message': 'Amount must be positive'}
    
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'Economy system not available'}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        balance = await get_balance(guild_id, user_id)
        
        if balance['coins'] < amount:
            return {'success': False, 'message': f'Insufficient funds. You have {balance["coins"]} coins in wallet.'}
        
        new_wallet = balance['coins'] - amount
        new_bank = balance['bank'] + amount
        
        supabase.table('user_economy').update({
            'coins': new_wallet,
            'bank': new_bank
        }).eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        return {'success': True, 'message': f'Deposited {amount} coins to bank!'}
    except Exception as e:
        logger.error(f"Failed to deposit: {e}")
        return {'success': False, 'message': f'Deposit failed: {str(e)}'}


async def withdraw_coins(guild_id: int, user_id: int, amount: int) -> dict:
    """
    Withdraw coins from bank to wallet.
    
    Returns:
        dict with keys: success, message
    """
    if amount <= 0:
        return {'success': False, 'message': 'Amount must be positive'}
    
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return {'success': False, 'message': 'Economy system not available'}
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        balance = await get_balance(guild_id, user_id)
        
        if balance['bank'] < amount:
            return {'success': False, 'message': f'Insufficient bank balance. You have {balance["bank"]} coins in bank.'}
        
        new_wallet = balance['coins'] + amount
        new_bank = balance['bank'] - amount
        
        supabase.table('user_economy').update({
            'coins': new_wallet,
            'bank': new_bank
        }).eq('guild_id', str(guild_id)).eq('user_id', str(user_id)).execute()
        
        return {'success': True, 'message': f'Withdrew {amount} coins from bank!'}
    except Exception as e:
        logger.error(f"Failed to withdraw: {e}")
        return {'success': False, 'message': f'Withdrawal failed: {str(e)}'}


async def get_richest_users(guild_id: int, limit: int = 10) -> list:
    """
    Get richest users in the guild (wallet + bank).
    
    Returns:
        List of dicts with keys: user_id, coins, bank, total
    """
    if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
        return []
    
    try:
        from supabase import create_client
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        response = supabase.table('user_economy').select('*').eq('guild_id', str(guild_id)).execute()
        
        if not response.data:
            return []
        
        # Calculate totals and sort
        users = []
        for user in response.data:
            total = user['coins'] + user['bank']
            users.append({
                'user_id': user['user_id'],
                'coins': user['coins'],
                'bank': user['bank'],
                'total': total
            })
        
        users.sort(key=lambda x: x['total'], reverse=True)
        return users[:limit]
    except Exception as e:
        logger.error(f"Failed to get richest users: {e}")
        return []
