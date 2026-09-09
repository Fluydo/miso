# -*- coding: utf-8 -*-
"""
cogs/economy.py
Economy commands - balance, pay, deposit, withdraw, leaderboard.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from functions.economy import (
    get_balance,
    get_economy_settings,
    transfer_coins,
    deposit_coins,
    withdraw_coins,
    get_richest_users
)

logger = logging.getLogger("miso.cogs.economy")


class Economy(commands.Cog):
    """Server economy system."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="balance", description="Check your or someone else's coin balance")
    @app_commands.describe(user="The user to check (defaults to yourself)")
    async def balance_command(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None
    ) -> None:
        """Check balance."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        target = user or interaction.user
        balance = await get_balance(interaction.guild.id, target.id)
        settings = await get_economy_settings(interaction.guild.id)

        symbol = settings.get('currency_symbol', '🪙')
        currency = settings.get('currency_name', 'coins')

        embed = discord.Embed(
            title=f"{symbol} {target.display_name}'s Balance",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="💰 Wallet",
            value=f"{symbol} **{balance['coins']:,}** {currency}",
            inline=True
        )

        embed.add_field(
            name="🏦 Bank",
            value=f"{symbol} **{balance['bank']:,}** {currency}",
            inline=True
        )

        total = balance['coins'] + balance['bank']
        embed.add_field(
            name="💎 Net Worth",
            value=f"{symbol} **{total:,}** {currency}",
            inline=True
        )

        embed.add_field(
            name="📊 Statistics",
            value=f"Earned: {symbol} {balance['total_earned']:,}\nSpent: {symbol} {balance['total_spent']:,}",
            inline=False
        )

        embed.set_thumbnail(url=target.display_avatar.url)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pay", description="Transfer coins to another user")
    @app_commands.describe(
        user="The user to pay",
        amount="Amount of coins to transfer"
    )
    async def pay_command(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int
    ) -> None:
        """Transfer coins."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't pay yourself!", ephemeral=True)
            return

        if user.bot:
            await interaction.response.send_message("❌ You can't pay bots!", ephemeral=True)
            return

        await interaction.response.defer()

        result = await transfer_coins(interaction.guild.id, interaction.user.id, user.id, amount)
        settings = await get_economy_settings(interaction.guild.id)
        symbol = settings.get('currency_symbol', '🪙')

        if result['success']:
            embed = discord.Embed(
                title="💸 Payment Successful",
                description=f"{interaction.user.mention} paid {user.mention} {symbol} **{amount:,}**",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Payment Failed",
                description=result['message'],
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="deposit", description="Deposit coins from wallet to bank")
    @app_commands.describe(amount="Amount to deposit (or 'all')")
    async def deposit_command(
        self,
        interaction: discord.Interaction,
        amount: str
    ) -> None:
        """Deposit to bank."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        # Handle 'all' keyword
        if amount.lower() == 'all':
            balance = await get_balance(interaction.guild.id, interaction.user.id)
            amount_int = balance['coins']
        else:
            try:
                amount_int = int(amount)
            except ValueError:
                await interaction.followup.send("❌ Invalid amount. Use a number or 'all'.", ephemeral=True)
                return

        result = await deposit_coins(interaction.guild.id, interaction.user.id, amount_int)
        settings = await get_economy_settings(interaction.guild.id)
        symbol = settings.get('currency_symbol', '🪙')

        if result['success']:
            embed = discord.Embed(
                title="🏦 Deposit Successful",
                description=f"Deposited {symbol} **{amount_int:,}** to your bank",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Deposit Failed",
                description=result['message'],
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="withdraw", description="Withdraw coins from bank to wallet")
    @app_commands.describe(amount="Amount to withdraw (or 'all')")
    async def withdraw_command(
        self,
        interaction: discord.Interaction,
        amount: str
    ) -> None:
        """Withdraw from bank."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        # Handle 'all' keyword
        if amount.lower() == 'all':
            balance = await get_balance(interaction.guild.id, interaction.user.id)
            amount_int = balance['bank']
        else:
            try:
                amount_int = int(amount)
            except ValueError:
                await interaction.followup.send("❌ Invalid amount. Use a number or 'all'.", ephemeral=True)
                return

        result = await withdraw_coins(interaction.guild.id, interaction.user.id, amount_int)
        settings = await get_economy_settings(interaction.guild.id)
        symbol = settings.get('currency_symbol', '🪙')

        if result['success']:
            embed = discord.Embed(
                title="💰 Withdrawal Successful",
                description=f"Withdrew {symbol} **{amount_int:,}** from your bank",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Withdrawal Failed",
                description=result['message'],
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rich", description="View the server's richest members")
    async def rich_command(self, interaction: discord.Interaction) -> None:
        """Show richest users leaderboard."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        richest = await get_richest_users(interaction.guild.id, limit=10)
        settings = await get_economy_settings(interaction.guild.id)
        symbol = settings.get('currency_symbol', '🪙')

        if not richest:
            await interaction.followup.send("No economy data available yet!")
            return

        embed = discord.Embed(
            title=f"{symbol} Richest Members",
            description="Top 10 users by total wealth (wallet + bank)",
            color=discord.Color.gold()
        )

        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]

        for idx, user_data in enumerate(richest, 1):
            try:
                user = await self.bot.fetch_user(int(user_data['user_id']))
                name = user.display_name
            except:
                name = f"User {user_data['user_id']}"

            medal = medals[idx - 1] if idx <= 3 else f"`#{idx}`"
            total = user_data['total']
            leaderboard_text += f"{medal} **{name}** — {symbol} {total:,}\n"

        embed.description = leaderboard_text
        embed.set_footer(text=f"💡 Earn coins from chatting, voice, and /daily")

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
