"""
cogs/daily.py
Daily rewards and streak system.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands

from functions.daily_streaks import claim_daily_reward, get_streak_data

logger = logging.getLogger("miso.cogs.daily")


class Daily(commands.Cog):
    """Daily login rewards and streak tracking."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="daily", description="Claim your daily reward and maintain your streak!")
    async def daily_command(self, interaction: discord.Interaction) -> None:
        """Claim daily rewards."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        result = await claim_daily_reward(interaction.guild.id, interaction.user.id)

        if result['success']:
            # Award XP and coins
            from functions.levels import add_xp_raw
            from functions.economy import add_coins
            
            try:
                add_xp_raw(interaction.guild.id, interaction.user.id, result['bonus_xp'])
            except:
                pass
            
            try:
                await add_coins(interaction.guild.id, interaction.user.id, result['bonus_coins'], 'daily_reward')
            except:
                pass
            
            # Create success embed
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                color=discord.Color.gold()
            )
            
            # Streak display with fire emoji
            streak_emoji = "🔥" * min(result['streak'], 5)
            embed.add_field(
                name=f"{streak_emoji} Current Streak",
                value=f"**{result['streak']} days**",
                inline=True
            )
            
            embed.add_field(
                name="🏆 Longest Streak",
                value=f"**{result['longest_streak']} days**",
                inline=True
            )
            
            embed.add_field(
                name="\u200b",  # Empty field for spacing
                value="\u200b",
                inline=True
            )
            
            # Rewards
            embed.add_field(
                name="⭐ XP Earned",
                value=f"+**{result['bonus_xp']}** XP",
                inline=True
            )
            
            embed.add_field(
                name="🪙 Coins Earned",
                value=f"+**{result['bonus_coins']}** coins",
                inline=True
            )
            
            embed.add_field(
                name="\u200b",
                value="\u200b",
                inline=True
            )
            
            # Streak milestone messages
            if result['streak'] >= 30:
                embed.description = "🎉 **30 DAY STREAK!** You're on fire! (3x rewards)"
            elif result['streak'] >= 14:
                embed.description = "🌟 **2 WEEK STREAK!** Amazing dedication! (2.5x rewards)"
            elif result['streak'] >= 7:
                embed.description = "⭐ **7 DAY STREAK!** Keep it up! (2x rewards)"
            elif result['streak'] >= 3:
                embed.description = "🔥 **3 DAY STREAK!** You're building momentum! (1.5x rewards)"
            else:
                embed.description = "Come back tomorrow to build your streak!"
            
            if result['was_broken']:
                embed.set_footer(text="⚠️ Your streak was reset. Start building it again!")
            else:
                embed.set_footer(text="💡 Claim daily to increase your streak multiplier!")
            
            await interaction.followup.send(embed=embed)
            
        else:
            # Already claimed or error
            embed = discord.Embed(
                title="❌ Cannot Claim",
                description=result['message'],
                color=discord.Color.red()
            )
            
            if result['streak'] > 0:
                embed.add_field(
                    name="🔥 Current Streak",
                    value=f"**{result['streak']} days**",
                    inline=True
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="streak", description="View your daily login streak")
    async def streak_command(self, interaction: discord.Interaction) -> None:
        """View streak information."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        streak_data = await get_streak_data(interaction.guild.id, interaction.user.id)

        embed = discord.Embed(
            title=f"🔥 {interaction.user.display_name}'s Streak",
            color=discord.Color.orange()
        )

        # Current streak with fire emoji
        streak_emoji = "🔥" * min(streak_data['current_streak'], 5)
        embed.add_field(
            name=f"{streak_emoji} Current Streak",
            value=f"**{streak_data['current_streak']} days**",
            inline=True
        )

        embed.add_field(
            name="🏆 Best Streak",
            value=f"**{streak_data['longest_streak']} days**",
            inline=True
        )

        embed.add_field(
            name="📅 Total Claims",
            value=f"**{streak_data['total_claims']}** times",
            inline=True
        )

        # Next reward info
        if streak_data['can_claim_today']:
            embed.add_field(
                name="✅ Status",
                value="Ready to claim `/daily`!",
                inline=False
            )
        else:
            embed.add_field(
                name="⏰ Status",
                value="Already claimed today. Come back tomorrow!",
                inline=False
            )

        # Show multipliers
        embed.add_field(
            name="💎 Streak Multipliers",
            value="3 days: **1.5x** rewards\n7 days: **2x** rewards\n14 days: **2.5x** rewards\n30 days: **3x** rewards",
            inline=False
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Daily(bot))
