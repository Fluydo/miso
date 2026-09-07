"""
cogs/stats.py
Personal statistics command - comprehensive user profile stats.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger("miso.cogs.stats")


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View comprehensive statistics for yourself or another user")
    @app_commands.describe(user="The user to check stats for (leave empty for yourself)")
    async def stats(self, interaction: discord.Interaction, user: discord.Member = None) -> None:
        """Show comprehensive user statistics."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        target_user = user or interaction.user
        await interaction.response.defer()

        try:
            # Gather all stats
            from functions.levels import get_user_level
            from functions.voice_xp import get_user_voice_stats
            from functions.economy import get_balance
            from functions.daily_streaks import get_streak_data
            from functions.achievements import get_user_achievements, get_all_achievements

            # Level stats
            level, xp, next_xp, rank = get_user_level(interaction.guild.id, target_user.id)

            # Voice stats
            voice_stats = await get_user_voice_stats(interaction.guild.id, target_user.id)
            total_voice_minutes = voice_stats.get('total_minutes', 0)
            total_voice_sessions = voice_stats.get('total_sessions', 0)

            # Economy stats
            economy = await get_balance(interaction.guild.id, target_user.id)
            total_coins = economy['wallet'] + economy['bank']
            
            # Daily streak
            streak_data = await get_streak_data(interaction.guild.id, target_user.id)
            current_streak = streak_data.get('current_streak', 0)
            longest_streak = streak_data.get('longest_streak', 0)

            # Achievements
            user_achievements = await get_user_achievements(interaction.guild.id, target_user.id)
            all_achievements = await get_all_achievements()
            unlocked_count = len(user_achievements)
            total_count = len(all_achievements)

            # Create embed
            embed = discord.Embed(
                title=f"📊 Statistics for {target_user.display_name}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)

            # Levels section
            progress = (xp / next_xp) * 100 if next_xp > 0 else 0
            embed.add_field(
                name="📈 Leveling",
                value=(
                    f"**Level:** {level}\n"
                    f"**Rank:** #{rank}\n"
                    f"**XP:** {xp:,}/{next_xp:,} ({progress:.1f}%)"
                ),
                inline=True
            )

            # Economy section
            embed.add_field(
                name="💰 Economy",
                value=(
                    f"**Total Coins:** {total_coins:,}\n"
                    f"**Wallet:** {economy['wallet']:,}\n"
                    f"**Bank:** {economy['bank']:,}\n"
                    f"**Total Earned:** {economy['total_earned']:,}"
                ),
                inline=True
            )

            # Voice section
            hours = total_voice_minutes // 60
            minutes = total_voice_minutes % 60
            embed.add_field(
                name="🎤 Voice Activity",
                value=(
                    f"**Total Time:** {hours}h {minutes}m\n"
                    f"**Sessions:** {total_voice_sessions}\n"
                    f"**Average:** {total_voice_minutes // total_voice_sessions if total_voice_sessions > 0 else 0}m/session"
                ),
                inline=True
            )

            # Streaks section
            streak_emoji = "🔥" * min(current_streak, 5) if current_streak > 0 else "❄️"
            embed.add_field(
                name="📅 Daily Streaks",
                value=(
                    f"{streak_emoji}\n"
                    f"**Current:** {current_streak} days\n"
                    f"**Longest:** {longest_streak} days\n"
                    f"**Total Claims:** {streak_data.get('total_claims', 0)}"
                ),
                inline=True
            )

            # Achievements section
            completion_pct = (unlocked_count / total_count * 100) if total_count > 0 else 0
            embed.add_field(
                name="🏆 Achievements",
                value=(
                    f"**Unlocked:** {unlocked_count}/{total_count}\n"
                    f"**Progress:** {completion_pct:.1f}%\n"
                    f"Use `/achievements` for details"
                ),
                inline=True
            )

            # Activity summary (if user is target)
            if target_user.id == interaction.user.id:
                embed.add_field(
                    name="📌 Quick Summary",
                    value=(
                        f"You're **#{rank}** on the leaderboard!\n"
                        f"Keep chatting and being active to level up! 🚀"
                    ),
                    inline=False
                )

            embed.set_footer(text=f"Member since {target_user.joined_at.strftime('%B %d, %Y') if target_user.joined_at else 'Unknown'}")
            embed.timestamp = datetime.utcnow()

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to fetch stats: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ Failed to fetch statistics. Some features may not be set up yet.",
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Stats(bot))
