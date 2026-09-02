# This is the NEW crash.py with ComponentV2 layout
# Rename this to crash.py on the OLD PC only!
# 
# Changes:
# - Uses ComponentV2 poll layout to embed bets list inside the message
# - No separate bets image message
# - Everything in one clean component

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
    """Buttons for crash game"""
    def __init__(self, bot, supabase_client):
        super().__init__(timeout=None)
        self.bot = bot
        self.supabase = supabase_client
    
    @discord.ui.button(label="Place Bet", style=discord.ButtonStyle.primary, custom_id="crash_bet_button", emoji="🎰")
    async def place_bet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CrashBetModal(self.bot, self.supabase))
    
    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.success, custom_id="crash_cashout_button", emoji="💰")
    async def cashout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[CASHOUT] Button clicked by user {interaction.user.id}")
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(interaction.user.id)
        
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data or result.data[0]['status'] != 'running':
            await interaction.followup.send("❌ No active crash game running!", ephemeral=True)
            return
            
        game = result.data[0]
        game_id = game['id']
        
        bet_result = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        
        if not bet_result.data:
            await interaction.followup.send("❌ You haven't placed a bet!", ephemeral=True)
            return
            
        bet = bet_result.data[0]
        
        if bet['cashed_out']:
            await interaction.followup.send("❌ You already cashed out!", ephemeral=True)
            return
            
        started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        current_mult = 1.0 * (1.08 ** elapsed)
        
        if current_mult >= game['crash_point']:
            await interaction.followup.send(f"💥 Game crashed at {game['crash_point']}x! You lost.", ephemeral=True)
            return
            
        winnings = int(bet['amount'] * current_mult)
        
        self.supabase.table('crash_bets').update({
            'cashed_out': True,
            'cashout_multiplier': current_mult
        }).eq('id', bet['id']).execute()
        
        add_balance(int(user_id), winnings)
        
        await interaction.followup.send(f"✅ Cashed out at {current_mult:.2f}x! Won {winnings} {COIN_EMOJI}", ephemeral=True)

class CrashBetModal(discord.ui.Modal, title="Place Crash Bet"):
    def __init__(self, bot, supabase_client):
        super().__init__()
        self.bot = bot
        self.supabase = supabase_client
        
    amount_input = discord.ui.TextInput(
        label="Bet Amount",
        placeholder="Enter amount (minimum 10 coins)",
        required=True,
        min_length=1,
        max_length=10,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            amount = int(self.amount_input.value)
        except ValueError:
            await interaction.followup.send("❌ Invalid amount! Must be a number.", ephemeral=True)
            return
            
        if amount < 10:
            await interaction.followup.send("❌ Minimum bet is 10 coins!", ephemeral=True)
            return
            
        user_id = str(interaction.user.id)
        balance = get_balance(int(user_id))
        
        if balance < amount:
            await interaction.followup.send(f"❌ Insufficient balance! You have {balance} {COIN_EMOJI}", ephemeral=True)
            return
            
        result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
        
        if not result.data or result.data[0]['status'] != 'betting':
            await interaction.followup.send("❌ Betting is closed for this round!", ephemeral=True)
            return
            
        game_id = result.data[0]['id']
        
        existing = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).eq('user_id', user_id).execute()
        
        if existing.data:
            await interaction.followup.send("❌ You already placed a bet this round!", ephemeral=True)
            return
            
        remove_balance(int(user_id), amount)
        
        self.supabase.table('crash_bets').insert({
            'game_id': game_id,
            'user_id': int(user_id),
            'amount': amount,
            'cashed_out': False,
            'cashout_multiplier': None
        }).execute()
        
        await interaction.followup.send(f"✅ Bet placed! {amount} {COIN_EMOJI} on this round.", ephemeral=True)

class Crash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.live_channel_id = None
        self.live_message_id = None
        self.last_multiplier = 1.0
        
    async def cog_load(self):
        self.crash_loop.start()
        self.update_live_embed.start()
        
    async def cog_unload(self):
        self.crash_loop.cancel()
        self.update_live_embed.cancel()
        
    def calculate_multiplier(self, elapsed_seconds: float) -> float:
        return round(1.0 * (1.08 ** elapsed_seconds), 2)
        
    def generate_crash_point(self) -> float:
        random_value = random.random()
        crash_multiplier = 1 + (random_value ** 8) * 34
        if random_value < 0.06:
            crash_multiplier = 1 + random.random() * 0.30
        return round(min(crash_multiplier, 35), 2)
        
    @app_commands.command(name="crashstart", description="[ADMIN] Start crash game live feed")
    @app_commands.checks.has_permissions(administrator=True)
    async def crashstart(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if self.live_channel_id and self.live_message_id:
            await interaction.followup.send("❌ Crash live feed already running!", ephemeral=True)
            return
            
        self.live_channel_id = interaction.channel_id
        
        embed = create_embed(
            title="🚀 Crash Game Live",
            description="Starting game...",
            color=discord.Color.purple()
        )
        
        view = CrashButtons(self.bot, self.supabase)
        message = await interaction.channel.send(embed=embed, view=view)
        self.live_message_id = message.id
        
        await interaction.followup.send(f"✅ Crash live feed started!", ephemeral=True)
        
    @tasks.loop(seconds=1)
    async def crash_loop(self):
        try:
            result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
            
            if not result.data:
                crash_point = self.generate_crash_point()
                self.supabase.table('crash_games').insert({
                    'status': 'betting',
                    'crash_point': crash_point,
                    'crash_at': crash_point,
                    'started_at': None,
                    'ended_at': None
                }).execute()
                return
                
            game = result.data[0]
            game_id = game['id']
            status = game['status']
            
            if status == 'betting':
                created_at = datetime.fromisoformat(game['created_at'].replace('Z', '+00:00'))
                elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
                
                if elapsed >= 10:
                    self.supabase.table('crash_games').update({
                        'status': 'running',
                        'started_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', game_id).execute()
                    
            elif status == 'running':
                started_at = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
                elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
                current_mult = self.calculate_multiplier(elapsed)
                
                if current_mult >= game['crash_point']:
                    self.supabase.table('crash_games').update({
                        'status': 'ended',
                        'ended_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', game_id).execute()
                    
            elif status == 'ended':
                ended_at = datetime.fromisoformat(game['ended_at'].replace('Z', '+00:00'))
                elapsed = (datetime.now(timezone.utc) - ended_at).total_seconds()
                
                if elapsed >= 2:
                    crash_point = self.generate_crash_point()
                    self.supabase.table('crash_games').insert({
                        'status': 'betting',
                        'crash_point': crash_point,
                        'crash_at': crash_point,
                        'started_at': None,
                        'ended_at': None
                    }).execute()
                    
        except Exception as e:
            print(f"Crash loop error: {e}")
            
    @tasks.loop(seconds=1)
    async def update_live_embed(self):
        if not self.live_channel_id or not self.live_message_id:
            return
            
        try:
            channel = self.bot.get_channel(self.live_channel_id)
            if not channel:
                return
                
            result = self.supabase.table('crash_games').select('*').order('created_at', desc=True).limit(1).execute()
            
            if not result.data:
                return
                
            game = result.data[0]
            game_id = game['id']
            
            # Get bets for this game
            bets_result = self.supabase.table('crash_bets').select('*').eq('game_id', game_id).execute()
            bet_list = bets_result.data or []
            
            temp_gif_path = tempfile.mktemp(suffix='.gif')
            
            if game['status'] == 'betting':
                generate_crash_gif('betting', countdown=10, bets=bet_list, output_path=temp_gif_path)
                
                title = "🎰 Betting Phase"
                description = f"# 1.00x\n\nPlace your bets now!"
                color = discord.Color.gold()
                
            elif game['status'] == 'running':
                started = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                current_mult = self.calculate_multiplier(elapsed)
                
                supersonic = current_mult >= 5.0
                phase = 'supersonic' if supersonic else 'running'
                
                generate_crash_gif(phase, multiplier=current_mult, start_mult=self.last_multiplier, output_path=temp_gif_path)
                
                self.last_multiplier = current_mult
                
                if supersonic:
                    title = "🔥 SUPERSONIC MODE"
                    color = discord.Color.orange()
                else:
                    title = "🚀 Flying"
                    color = discord.Color.green()
                    
                description = f"# {current_mult:.2f}x\n\nCash out now!"
            else:
                generate_crash_gif('crashed', multiplier=game['crash_point'], output_path=temp_gif_path)
                
                self.last_multiplier = 1.0
                
                title = "💥 CRASHED!"
                description = f"Crashed at **{game['crash_point']:.2f}x**\n\nNext round in 2s..."
                color = discord.Color.red()
            
            # Add bets list to description
            description += "\n\n**Current Round Bets:**\n"
            if bet_list:
                for bet in bet_list[:10]:  # Show up to 10 bets
                    user_id = bet['user_id']
                    amount = bet['amount']
                    if bet['cashed_out']:
                        mult = bet.get('cashout_multiplier', 0)
                        description += f"<@{user_id}>: {amount} {COIN_EMOJI} → Cashed at **{mult:.2f}x** ✅\n"
                    else:
                        description += f"<@{user_id}>: {amount} {COIN_EMOJI}\n"
                if len(bet_list) > 10:
                    description += f"*... and {len(bet_list) - 10} more*\n"
            else:
                description += "*No bets yet*\n"
            
            description += "\n-# Play on the [website](https://miso-dashboard-iota.vercel.app/games/crash) for better experience"
            
            embed = create_embed(title=title, description=description, color=color)
            embed.set_image(url="attachment://crash.gif")
            embed.set_footer(text=f"{len(bet_list)} players • Live updates")
            
            view = CrashButtons(self.bot, self.supabase)
            gif_file = discord.File(temp_gif_path, filename="crash.gif")
            
            try:
                message = await channel.fetch_message(self.live_message_id)
                await message.edit(embed=embed, attachments=[gif_file], view=view)
            except discord.NotFound:
                new_msg = await channel.send(embed=embed, file=gif_file, view=view)
                self.live_message_id = new_msg.id
            
            try:
                os.remove(temp_gif_path)
            except:
                pass
                
        except Exception as e:
            print(f"Live embed update error: {e}")
            
    @update_live_embed.before_loop
    async def before_update_live_embed(self):
        await self.bot.wait_until_ready()
        
    @crash_loop.before_loop
    async def before_crash_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Crash(bot))
