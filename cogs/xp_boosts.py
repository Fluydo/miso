"""
cogs/xp_boosts.py
Commands for managing XP boost events.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger("miso.cogs.xp_boosts")


class XPBoosts(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    xpboost_group = app_commands.Group(name="xpboost", description="Manage XP boost events")

    @xpboost_group.command(name="start", description="Start an XP boost event (Admin only)")
    @app_commands.describe(
        multiplier="XP multiplier (e.g., 2.0 for 2x XP, 1.5 for 1.5x)",
        duration="Duration in hours",
        reason="Optional reason for the boost"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def xpboost_start(
        self,
        interaction: discord.Interaction,
        multiplier: float,
        duration: int,
        reason: str = None
    ) -> None:
        """Start an XP boost event."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        if multiplier < 1.0 or multiplier > 10.0:
            await interaction.response.send_message("❌ Multiplier must be between 1.0 and 10.0!", ephemeral=True)
            return

        if duration < 1 or duration > 168:  # Max 1 week
            await interaction.response.send_message("❌ Duration must be between 1 and 168 hours (1 week)!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.xp_boosts import create_boost_event

        result = await create_boost_event(
            guild_id=interaction.guild.id,
            started_by=interaction.user.id,
            multiplier=multiplier,
            duration_hours=duration,
            reason=reason
        )

        if result['success']:
            # Announce to server
            embed = discord.Embed(
                title="🚀 XP Boost Event Started!",
                description=f"**{multiplier}x XP** is now active for the next **{duration} hours**!",
                color=discord.Color.gold()
            )
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Started by {interaction.user.display_name}")
            embed.timestamp = datetime.utcnow()

            # Try to send to general or first available channel
            announcement_channel = None
            for channel in interaction.guild.text_channels:
                if channel.permissions_for(interaction.guild.me).send_messages:
                    announcement_channel = channel
                    break

            if announcement_channel:
                try:
                    await announcement_channel.send(embed=embed)
                except:
                    pass

            await interaction.followup.send(f"✅ {result['message']}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)

    @xpboost_group.command(name="end", description="End the current XP boost event (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def xpboost_end(self, interaction: discord.Interaction) -> None:
        """End the active XP boost."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.xp_boosts import end_boost_event, get_active_boost

        active = await get_active_boost(interaction.guild.id)
        if not active:
            await interaction.followup.send("❌ There is no active XP boost event!", ephemeral=True)
            return

        success = await end_boost_event(interaction.guild.id)

        if success:
            # Announce end
            embed = discord.Embed(
                title="⏰ XP Boost Event Ended",
                description=f"The **{active['multiplier']}x XP** boost has ended. Thanks for participating!",
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Ended by {interaction.user.display_name}")
            embed.timestamp = datetime.utcnow()

            # Try to send to general or first available channel
            announcement_channel = None
            for channel in interaction.guild.text_channels:
                if channel.permissions_for(interaction.guild.me).send_messages:
                    announcement_channel = channel
                    break

            if announcement_channel:
                try:
                    await announcement_channel.send(embed=embed)
                except:
                    pass

            await interaction.followup.send("✅ XP boost event has been ended!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to end the boost event.", ephemeral=True)

    @xpboost_group.command(name="status", description="Check the current XP boost status")
    async def xpboost_status(self, interaction: discord.Interaction) -> None:
        """Check XP boost status."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        from functions.xp_boosts import get_active_boost

        active = await get_active_boost(interaction.guild.id)

        if not active:
            embed = discord.Embed(
                title="📊 XP Boost Status",
                description="There is currently **no active XP boost** event.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Admins can start one with /xpboost start")
        else:
            end_time = datetime.fromisoformat(active['end_time'])
            time_left = end_time - datetime.utcnow()
            hours_left = int(time_left.total_seconds() // 3600)
            minutes_left = int((time_left.total_seconds() % 3600) // 60)

            embed = discord.Embed(
                title="🚀 XP Boost Active!",
                description=f"**{active['multiplier']}x XP** is currently active!",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="⏱️ Time Remaining",
                value=f"{hours_left}h {minutes_left}m",
                inline=True
            )
            embed.add_field(
                name="🎯 Multiplier",
                value=f"{active['multiplier']}x",
                inline=True
            )
            if active.get('reason'):
                embed.add_field(name="📝 Reason", value=active['reason'], inline=False)

            try:
                started_by = await self.bot.fetch_user(int(active['started_by']))
                embed.set_footer(text=f"Started by {started_by.display_name}")
            except:
                pass

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    cog = XPBoosts(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.xpboost_group)
