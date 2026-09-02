import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import random
import tempfile
import os
from datetime import datetime, timezone
from functions.economy import get_balance, add_balance, remove_balance
from embeds.utility import create_embed
from config import EMOJI_COIN as COIN_EMOJI, SUPABASE_URL, SUPABASE_SERVICE_KEY
from supabase import create_client, Client
from functions.renderer import generate_crash_gif

class CrashButtons(discord.ui.View):
    """Buttons for crash game embed"""
    def __init__(self, bot, supabase_client):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.supabase = supabase_client
    
    @discord.ui.button(label="Place Bet", style=discord.ButtonStyle.primary, custom_id="crash_bet_button", emoji="🎰")
    async def place_bet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to place a bet"""
        await interaction.response.send_modal(CrashBetModal(self.bot, self.supabase))
    
    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.success, custom_id="crash_cashout_button", emoji="💰")
    async def cashout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to cash out"""
        print(f"[CASHOUT] Button clicked by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(interaction.user.id)  # Convert to string for Supabase
        print(f"[CASHOUT] User ID: {user_id}")
        
        # Get current game
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        print(f"[CASHOUT] Game query result: {result.data}")
        
        if not result.data or result.data[0]['status'] != 'running':
            print(f"[CASHOUT] Game not running. Status: {result.data[0]['status'] if result.data else 'No game'}")
            await interaction.followup.send("❌ No active crash game running!", ephemeral=True)
            return
            
        game = result.data[0]
        game_id = game['id']
        print(f"[CASHOUT] Game ID: {game_id}")
        
        # Get user's bet
        bet_result = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        print(f"[CASHOUT] Bet query result: {bet_result.data}")
        
        if not bet_result.data:
            print(f"[CASHOUT] No bet found for user {user_id} in game {game_id}")
            # Check all bets for this game
            all_bets = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).execute()
            print(f"[CASHOUT] All bets in game: {all_bets.data}")
            await interaction.followup.send("❌ You haven't placed a bet!", ephemeral=True)
            return
            
        bet = bet_result.data[0]
        print(f"[CASHOUT] Bet found: {bet}")
        
        if bet['cashed_out']:
            print(f"[CASHOUT] Bet already cashed out")
            await interaction.followup.send("❌ You already cashed out!", ephemeral=True)
            return
            
        # Calculate current multiplier
        started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        current_mult = self.calculate_multiplier(elapsed)
        print(f"[CASHOUT] Current multiplier: {current_mult}, Crash point: {game['crash_point']}")
        
        # Check if crashed
        if current_mult >= game['crash_point']:
            print(f"[CASHOUT] Game already crashed!")
            await interaction.followup.send(f"💥 Game crashed at {game['crash_point']}x! You lost.", ephemeral=True)
            return
            
        # Cash out
        winnings = int(bet['amount'] * current_mult)
        print(f"[CASHOUT] Cashing out: bet={bet['amount']}, mult={current_mult}, winnings={winnings}")
        
        update_result = self.supabase.table('crash_bets').update({
            'cashed_out': True,
            'cashout_multiplier': current_mult
        }).eq('id', bet['id']).execute()
        print(f"[CASHOUT] Update result: {update_result.data}")
        
        add_balance(int(user_id), winnings)  # Convert back to int for balance functions
        print(f"[CASHOUT] Added {winnings} to balance")
        
        await interaction.followup.send(f"✅ Cashed out at {current_mult}x! Won {winnings} {COIN_EMOJI}", ephemeral=True)
        print(f"[CASHOUT] Success!")

class CrashBetModal(discord.ui.Modal, title="Place Crash Bet"):
    """Modal for placing a crash bet"""
    def __init__(self, bot, supabase_client):
        super().__init__()
        self.bot = bot
        self.supabase = supabase_client
    
    bet_amount = discord.ui.TextInput(
        label="Bet Amount",
        placeholder="Enter amount (minimum 10 coins)",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            amount = int(self.bet_amount.value)
        except ValueError:
            await interaction.followup.send("❌ Invalid amount! Please enter a number.", ephemeral=True)
            return
        
        user_id = interaction.user.id
        
        if amount < 10:
            await interaction.followup.send(f"❌ Minimum bet is 10 {COIN_EMOJI}", ephemeral=True)
            return
            
        balance = get_balance(user_id)
        if balance < amount:
            await interaction.followup.send(f"❌ Insufficient balance! You have {balance} {COIN_EMOJI}", ephemeral=True)
            return
            
        # Get current game
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data or result.data[0]['status'] != 'betting':
            await interaction.followup.send("❌ Betting is closed! Wait for next round.", ephemeral=True)
            return
            
        game_id = result.data[0]['id']
        
        # Check if already bet
        existing = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        if existing.data:
            await interaction.followup.send("❌ You already placed a bet this round!", ephemeral=True)
            return
            
        # Deduct balance
        if not remove_balance(user_id, amount):
            await interaction.followup.send("❌ Failed to place bet!", ephemeral=True)
            return
            
        # Record bet
        self.supabase.table('crash_bets').insert({
            'game_id': game_id,
            'user_id': user_id,
            'amount': amount,
            'cashed_out': False,
            'cashout_multiplier': None
        }).execute()
        
        await interaction.followup.send(f"✅ Bet placed: {amount} {COIN_EMOJI}", ephemeral=True)

class Crash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.crash_channel_id = None  # Set via /crashsetup command
        self.live_message_id = None
        self.last_multiplier = 1.0  # Track last multiplier for GIF continuity
        self.crash_loop.start()
        self.update_live_embed.start()
    
    @staticmethod
    def calculate_multiplier(elapsed_seconds: float) -> float:
        """
        Calculate exponential multiplier based on elapsed time.
        Formula: 1.0 * (1.08 ** elapsed)
        
        This creates a curve where:
        - 0s = 1.00x
        - 5s = 1.47x
        - 10s = 2.16x
        - 15s = 3.17x
        - 20s = 4.66x (supersonic starts at 5x around 21s)
        - 25s = 6.85x
        - 30s = 10.06x
        
        Growth accelerates over time, matching visual rocket trajectory.
        """
        return round(1.0 * (1.08 ** elapsed_seconds), 2)
        
    def cog_unload(self):
        self.crash_loop.cancel()
        self.update_live_embed.cancel()
        
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
                started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
                running_elapsed = (now - started).total_seconds()
                
                # Check if crash point is reached
                if running_elapsed >= game['crash_at']:
                    # End game
                    await self._end_game(game['id'])
            elif game['status'] == 'ended':
                # Game ended, wait 2 seconds then start new one
                ended = datetime.fromisoformat(game['ended_at'].replace('Z', '+00:00')) if game.get('ended_at') else created
                ended_elapsed = (now - ended).total_seconds()
                
                if ended_elapsed >= 2:
                    await self._start_new_game()
        except Exception as e:
            print(f"Crash loop error: {e}")
            import traceback
            traceback.print_exc()
            
    @crash_loop.before_loop
    async def before_crash_loop(self):
        await self.bot.wait_until_ready()
    
    @tasks.loop(seconds=2)
    async def update_live_embed(self):
        """Update live message in crash channel every 2 seconds - Component v2 format"""
        if not self.crash_channel_id or not self.live_message_id:
            return
            
        try:
            channel = self.bot.get_channel(self.crash_channel_id)
            if not channel:
                return
                
            # Get current game
            result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
            if not result.data:
                return
                
            game = result.data[0]
            
            # Get bets for current game
            bets_result = self.supabase.table('crash_bets').select('*').eq('game_id', game['id']).execute()
            
            # Format bet list sorted by amount (highest first)
            bet_lines = []
            for bet in sorted(bets_result.data, key=lambda x: x['amount'], reverse=True)[:10]:  # Top 10 only
                try:
                    user = await self.bot.fetch_user(int(bet['user_id']))
                    username = user.display_name
                except:
                    username = f"User{bet['user_id'][:4]}"
                
                if bet['cashed_out']:
                    mult = bet.get('cashout_multiplier', 0)
                    bet_lines.append(f"💰 **{username}** — {bet['amount']} {COIN_EMOJI} • Cashed @ {mult}x")
                elif game['status'] == 'ended':
                    bet_lines.append(f"❌ **{username}** — {bet['amount']} {COIN_EMOJI} • Lost")
                else:
                    bet_lines.append(f"🎰 **{username}** — {bet['amount']} {COIN_EMOJI} • Active")
            
            # Generate animated GIF for current phase
            temp_gif_path = os.path.join(tempfile.gettempdir(), f"crash_{game['id'][:8]}.gif")
            
            if game['status'] == 'betting':
                created = datetime.fromisoformat(game['created_at'].replace('Z', '+00:00'))
                elapsed = (datetime.now(timezone.utc) - created).total_seconds()
                countdown = max(0, int(10 - elapsed))
                
                generate_crash_gif('betting', countdown=countdown, output_path=temp_gif_path)
                self.last_multiplier = 1.0
                
                header = f"🎰 **BETTING PHASE**\nStarting in **{countdown} seconds** — Place your bets now!"
            elif game['status'] == 'running':
                started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                current_mult = self.calculate_multiplier(elapsed)
                
                supersonic = current_mult >= 5.0
                phase = 'supersonic' if supersonic else 'running'
                
                generate_crash_gif(phase, multiplier=current_mult, start_mult=self.last_multiplier, output_path=temp_gif_path)
                self.last_multiplier = current_mult
                
                if supersonic:
                    header = f"🔥 **SUPERSONIC — {current_mult}x**\n**DANGER ZONE!** Cash out before it crashes!"
                else:
                    header = f"🚀 **CRASH GAME — {current_mult}x**\nMultiplier climbing... Cash out anytime!"
            else:  # ended
                generate_crash_gif('crashed', multiplier=game['crash_point'], output_path=temp_gif_path)
                self.last_multiplier = 1.0
                
                header = f"💥 **CRASHED**\nCrashed at **{game['crash_point']}x** — Next round in 2s..."
            
            # Build message content (Component v2: content + GIF + buttons, NO embed)
            bet_count = len(bets_result.data)
            if bet_lines:
                bets_text = "\n".join(bet_lines)
                if bet_count > 10:
                    bets_text += f"\n\n*...and {bet_count - 10} more*"
            else:
                bets_text = "*No bets yet*"
            
            content = f"{header}\n\n**Current Bets ({bet_count})**\n{bets_text}\n\n-# Play on the [website](https://miso-dashboard-iota.vercel.app/games/crash) for a better experience"
            
            # Create view with buttons
            view = CrashButtons(self.bot, self.supabase)
            
            # Prepare GIF file
            gif_file = discord.File(temp_gif_path, filename="crash.gif")
            
            # Update message (Component v2 format: content + file + view, NO embed)
            try:
                message = await channel.fetch_message(self.live_message_id)
                await message.edit(content=content, attachments=[gif_file], view=view)
            except discord.NotFound:
                # Message deleted, create new one
                new_msg = await channel.send(content=content, file=gif_file, view=view)
                self.live_message_id = new_msg.id
            
            # Clean up temp file
            try:
                os.remove(temp_gif_path)
            except:
                pass
                
        except Exception as e:
            print(f"Live message update error: {e}")
            
    @update_live_embed.before_loop
    async def before_update_live_embed(self):
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
            current_mult = self.calculate_multiplier(elapsed)
            
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
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        if amount < 10:
            await interaction.followup.send(f"❌ Minimum bet is 10 {COIN_EMOJI}", ephemeral=True)
            return
            
        balance = get_balance(user_id)
        if balance < amount:
            await interaction.followup.send(f"❌ Insufficient balance! You have {balance} {COIN_EMOJI}", ephemeral=True)
            return
            
        # Get current game
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data or result.data[0]['status'] != 'betting':
            await interaction.followup.send("❌ Betting is closed! Wait for next round.", ephemeral=True)
            return
            
        game_id = result.data[0]['id']
        
        # Check if already bet
        existing = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        if existing.data:
            await interaction.followup.send("❌ You already placed a bet this round!", ephemeral=True)
            return
            
        # Deduct balance
        if not remove_balance(user_id, amount):
            await interaction.followup.send("❌ Failed to place bet!", ephemeral=True)
            return
            
        # Record bet
        self.supabase.table('crash_bets').insert({
            'game_id': game_id,
            'user_id': user_id,
            'amount': amount,
            'cashed_out': False,
            'cashout_multiplier': None
        }).execute()
        
        await interaction.followup.send(f"✅ Bet placed: {amount} {COIN_EMOJI}", ephemeral=True)
        
    @app_commands.command(name="cashout", description="Cash out of the crash game")
    async def crash_cashout(self, interaction: discord.Interaction):
        """Cash out at current multiplier"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        # Get current game
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data or result.data[0]['status'] != 'running':
            await interaction.followup.send("❌ No active crash game running!", ephemeral=True)
            return
            
        game = result.data[0]
        game_id = game['id']
        
        # Get user's bet
        bet_result = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        
        if not bet_result.data:
            await interaction.followup.send("❌ You haven't placed a bet!", ephemeral=True)
            return
            
        bet = bet_result.data[0]
        
        if bet['cashed_out']:
            await interaction.followup.send("❌ You already cashed out!", ephemeral=True)
            return
            
        # Calculate current multiplier
        started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        current_mult = self.calculate_multiplier(elapsed)
        
        # Check if crashed
        if current_mult >= game['crash_point']:
            await interaction.followup.send(f"💥 Game crashed at {game['crash_point']}x! You lost.", ephemeral=True)
            return
            
        # Cash out
        winnings = int(bet['amount'] * current_mult)
        
        self.supabase.table('crash_bets').update({
            'cashed_out': True,
            'cashout_multiplier': current_mult
        }).eq('id', bet['id']).execute()
        
        add_balance(user_id, winnings)
        
        await interaction.followup.send(f"✅ Cashed out at {current_mult}x! Won {winnings} {COIN_EMOJI}", ephemeral=True)
    
    @app_commands.command(name="crashsetup", description="Setup crash game live channel")
    @app_commands.default_permissions(administrator=True)
    async def crash_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Admin command to set up live crash channel - Component v2 (NO EMBED)"""
        self.crash_channel_id = channel.id
        
        # Create initial message (NO EMBED - just content + buttons)
        content = "🚀 **CRASH GAME LIVE**\n\nThis message will update every 2 seconds with the current game status."
        view = CrashButtons(self.bot, self.supabase)
        
        msg = await channel.send(content=content, view=view)
        self.live_message_id = msg.id
        
        await interaction.response.send_message(
            f"✅ Crash live channel set to {channel.mention}\nMessage ID: {msg.id}",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Crash(bot))
