import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timezone
from functions.economy import get_balance, add_balance, remove_balance
from embeds.utility import create_embed
from config import COIN_EMOJI, SUPABASE_URL, SUPABASE_SERVICE_KEY
from supabase import create_client, Client

class Crash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.crash_loop.start()
        
    def cog_unload(self):
        self.crash_loop.cancel()
        
    @tasks.loop(seconds=1)
    async def crash_loop(self):
        """Auto-restart crash game every round"""
        try:
            # Check current game state
            result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
            
            if not result.data:
                # No game exists, create first one
                await self._start_new_game()
                return
                
            game = result.data[0]
            now = datetime.now(timezone.utc)
            created = datetime.fromisoformat(game['created_at'].replace('Z', '+00:00'))
            elapsed = (now - created).total_seconds()
            
            if game['status'] == 'betting':
                # Betting phase lasts 10 seconds
                if elapsed >= 10:
                    # Start the crash
                    await self._start_crash(game['id'])
            elif game['status'] == 'running':
                # Crash is running, check if it should end
                if elapsed >= game['crash_at'] + 10:
                    # End game and start new one
                    await self._end_game(game['id'])
                    await asyncio.sleep(2)
                    await self._start_new_game()
        except Exception as e:
            print(f"Crash loop error: {e}")
            
    @crash_loop.before_loop
    async def before_crash_loop(self):
        await self.bot.wait_until_ready()
        
    async def _start_new_game(self):
        """Start a new crash game"""
        # Random crash point between 1.01x and 10.00x
        crash_point = round(random.uniform(1.01, 10.0), 2)
        
        game_data = {
            'status': 'betting',
            'crash_point': crash_point,
            'crash_at': 10 + random.uniform(2, 15),  # Runs for 2-15 seconds
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.supabase.table('crash_games').insert(game_data).execute()
        
    async def _start_crash(self, game_id: str):
        """Start the crash animation"""
        self.supabase.table('crash_games').update({
            'status': 'running',
            'started_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', game_id).execute()
        
    async def _end_game(self, game_id: str):
        """End the game and payout winners"""
        # Get all bets that cashed out
        bets = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('cashed_out', True).execute()
        
        for bet in bets.data:
            # Payout
            winnings = int(bet['amount'] * bet['cashout_multiplier'])
            add_balance(bet['user_id'], winnings)
            
        # Mark game as ended
        self.supabase.table('crash_games').update({
            'status': 'ended',
            'ended_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', game_id).execute()
        
    @app_commands.command(name="crash", description="View current crash game status")
    async def crash_info(self, interaction: discord.Interaction):
        """View current crash game"""
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data:
            await interaction.response.send_message("❌ No active crash game!", ephemeral=True)
            return
            
        game = result.data[0]
        
        if game['status'] == 'betting':
            embed = create_embed(
                title="🚀 Crash Game - Betting Phase",
                description=f"Place your bets now! Game starts in a few seconds.\n\nUse `/crashbet <amount>` to bet.",
                color=discord.Color.gold()
            )
        elif game['status'] == 'running':
            # Calculate current multiplier
            started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            current_mult = round(1.0 + (elapsed * 0.2), 2)  # Grows at 0.2x per second
            
            embed = create_embed(
                title="🚀 Crash Game - Running!",
                description=f"**Current Multiplier: {current_mult}x**\n\nUse `/cashout` to cash out now!",
                color=discord.Color.green()
            )
        else:
            embed = create_embed(
                title="💥 Game Ended",
                description=f"Crashed at **{game['crash_point']}x**\n\nNew game starting soon...",
                color=discord.Color.red()
            )
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="crashbet", description="Bet on the crash game")
    async def crash_bet(self, interaction: discord.Interaction, amount: int):
        """Place a bet on the active crash game"""
        user_id = interaction.user.id
        
        if amount < 10:
            await interaction.response.send_message(f"❌ Minimum bet is 10 {COIN_EMOJI}", ephemeral=True)
            return
            
        balance = get_balance(user_id)
        if balance < amount:
            await interaction.response.send_message(f"❌ Insufficient balance! You have {balance} {COIN_EMOJI}", ephemeral=True)
            return
            
        # Get current game
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data or result.data[0]['status'] != 'betting':
            await interaction.response.send_message("❌ Betting is closed! Wait for next round.", ephemeral=True)
            return
            
        game_id = result.data[0]['id']
        
        # Check if already bet
        existing = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        if existing.data:
            await interaction.response.send_message("❌ You already placed a bet this round!", ephemeral=True)
            return
            
        # Deduct balance
        if not remove_balance(user_id, amount):
            await interaction.response.send_message("❌ Failed to place bet!", ephemeral=True)
            return
            
        # Record bet
        self.supabase.table('crash_bets').insert({
            'game_id': game_id,
            'user_id': user_id,
            'amount': amount,
            'cashed_out': False,
            'cashout_multiplier': None
        }).execute()
        
        await interaction.response.send_message(f"✅ Bet placed: {amount} {COIN_EMOJI}", ephemeral=True)
        
    @app_commands.command(name="cashout", description="Cash out of the crash game")
    async def crash_cashout(self, interaction: discord.Interaction):
        """Cash out at current multiplier"""
        user_id = interaction.user.id
        
        # Get current game
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data or result.data[0]['status'] != 'running':
            await interaction.response.send_message("❌ No active crash game running!", ephemeral=True)
            return
            
        game = result.data[0]
        game_id = game['id']
        
        # Get user's bet
        bet_result = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        
        if not bet_result.data:
            await interaction.response.send_message("❌ You haven't placed a bet!", ephemeral=True)
            return
            
        bet = bet_result.data[0]
        
        if bet['cashed_out']:
            await interaction.response.send_message("❌ You already cashed out!", ephemeral=True)
            return
            
        # Calculate current multiplier
        started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        current_mult = round(1.0 + (elapsed * 0.2), 2)
        
        # Check if crashed
        if current_mult >= game['crash_point']:
            await interaction.response.send_message(f"💥 Game crashed at {game['crash_point']}x! You lost.", ephemeral=True)
            return
            
        # Cash out
        winnings = int(bet['amount'] * current_mult)
        
        self.supabase.table('crash_bets').update({
            'cashed_out': True,
            'cashout_multiplier': current_mult
        }).eq('id', bet['id']).execute()
        
        add_balance(user_id, winnings)
        
        await interaction.response.send_message(f"✅ Cashed out at {current_mult}x! Won {winnings} {COIN_EMOJI}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Crash(bot))
