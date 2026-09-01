import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from functions.economy import get_balance, set_balance
from embeds.utility import create_embed
from config import COIN_EMOJI

class Crash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # guild_id: {crash_point, bets: {user_id: amount}, gif_url}
        
    @app_commands.command(name="crash", description="Start a crash game")
    @app_commands.default_permissions(administrator=True)
    async def crash_start(self, interaction: discord.Interaction, gif_url: str):
        """Admin command to start a crash game with a GIF"""
        guild_id = interaction.guild_id
        
        if guild_id in self.active_games:
            await interaction.response.send_message("❌ A crash game is already running!", ephemeral=True)
            return
            
        # Parse crash point from admin (they know when it crashes)
        await interaction.response.send_message("What's the crash multiplier? (e.g., 2.5)", ephemeral=True)
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
            
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            crash_point = float(msg.content)
            await msg.delete()
        except (asyncio.TimeoutError, ValueError):
            return
            
        # Initialize game
        self.active_games[guild_id] = {
            'crash_point': crash_point,
            'bets': {},
            'cashed_out': {},
            'gif_url': gif_url
        }
        
        # Create betting embed
        embed = create_embed(
            title="🚀 Crash Game Started!",
            description=f"Place your bets using `/crashbet <amount>`\nCash out anytime with `/crashout`\n\n{gif_url}",
            color=discord.Color.gold()
        )
        embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="crashbet", description="Bet on the crash game")
    async def crash_bet(self, interaction: discord.Interaction, amount: int):
        """Place a bet on the active crash game"""
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        
        if guild_id not in self.active_games:
            await interaction.response.send_message("❌ No active crash game!", ephemeral=True)
            return
            
        if user_id in self.active_games[guild_id]['bets']:
            await interaction.response.send_message("❌ You already placed a bet!", ephemeral=True)
            return
            
        balance = await get_balance(user_id)
        
        if balance < amount:
            await interaction.response.send_message(f"❌ Insufficient balance! You have {balance} {COIN_EMOJI}", ephemeral=True)
            return
            
        if amount < 10:
            await interaction.response.send_message(f"❌ Minimum bet is 10 {COIN_EMOJI}", ephemeral=True)
            return
            
        # Deduct bet
        await set_balance(user_id, balance - amount)
        self.active_games[guild_id]['bets'][user_id] = amount
        
        await interaction.response.send_message(f"✅ Bet placed: {amount} {COIN_EMOJI}", ephemeral=True)
        
    @app_commands.command(name="cashout", description="Cash out of the crash game")
    async def crash_cashout(self, interaction: discord.Interaction, multiplier: float):
        """Cash out at a specific multiplier"""
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        
        if guild_id not in self.active_games:
            await interaction.response.send_message("❌ No active crash game!", ephemeral=True)
            return
            
        game = self.active_games[guild_id]
        
        if user_id not in game['bets']:
            await interaction.response.send_message("❌ You haven't placed a bet!", ephemeral=True)
            return
            
        if user_id in game['cashed_out']:
            await interaction.response.send_message("❌ You already cashed out!", ephemeral=True)
            return
            
        # Check if multiplier is valid
        if multiplier > game['crash_point']:
            await interaction.response.send_message(f"❌ Game crashed at {game['crash_point']}x! You lost.", ephemeral=True)
            game['cashed_out'][user_id] = {'multiplier': multiplier, 'won': False}
            return
            
        # Calculate winnings
        bet_amount = game['bets'][user_id]
        winnings = int(bet_amount * multiplier)
        
        balance = await get_balance(user_id)
        await set_balance(user_id, balance + winnings)
        
        game['cashed_out'][user_id] = {'multiplier': multiplier, 'won': True, 'amount': winnings}
        
        await interaction.response.send_message(f"✅ Cashed out at {multiplier}x! Won {winnings} {COIN_EMOJI}", ephemeral=True)
        
    @app_commands.command(name="crashend", description="End the crash game and show results")
    @app_commands.default_permissions(administrator=True)
    async def crash_end(self, interaction: discord.Interaction):
        """Admin command to end the crash game"""
        guild_id = interaction.guild_id
        
        if guild_id not in self.active_games:
            await interaction.response.send_message("❌ No active crash game!", ephemeral=True)
            return
            
        game = self.active_games[guild_id]
        crash_point = game['crash_point']
        
        # Create results embed
        embed = create_embed(
            title=f"💥 Game Crashed at {crash_point}x!",
            description="",
            color=discord.Color.red()
        )
        
        winners = []
        losers = []
        
        for user_id, bet_amount in game['bets'].items():
            user = await self.bot.fetch_user(user_id)
            if user_id in game['cashed_out'] and game['cashed_out'][user_id]['won']:
                cashout = game['cashed_out'][user_id]
                winners.append(f"{user.mention}: {bet_amount} → {cashout['amount']} {COIN_EMOJI} ({cashout['multiplier']}x)")
            else:
                losers.append(f"{user.mention}: Lost {bet_amount} {COIN_EMOJI}")
                
        if winners:
            embed.add_field(name="✅ Winners", value="\n".join(winners), inline=False)
        if losers:
            embed.add_field(name="❌ Losers", value="\n".join(losers), inline=False)
            
        await interaction.response.send_message(embed=embed)
        
        # Clean up
        del self.active_games[guild_id]

async def setup(bot):
    await bot.add_cog(Crash(bot))
