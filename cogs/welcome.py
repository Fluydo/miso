"""
cogs/welcome.py
Welcome & Leave greetings with custom visual image cards.
"""

import io
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
from functions.renderer import render_leave_card, render_welcome_card
from functions.welcome import (
    get_welcome_channels,
    set_leave_channel,
    set_welcome_channel,
)

logger = logging.getLogger("miso.cogs.welcome")


class Welcome(commands.Cog):
    """Server welcome and leave greeting announcements."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        w_id, _ = get_welcome_channels(member.guild.id)
        if not w_id:
            return

        channel = member.guild.get_channel(w_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        try:
            png_bytes = await render_welcome_card(
                avatar_url=member.display_avatar.url,
                username=member.name,
                member_count=member.guild.member_count or len(member.guild.members),
                server_name=member.guild.name,
            )
            file = discord.File(io.BytesIO(png_bytes), filename="welcome.png")
            await channel.send(
                content=f"Welcome {member.mention} to **{member.guild.name}**!",
                file=file,
            )
        except Exception as e:
            logger.error(f"Failed to send welcome card in {member.guild.name}: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.bot:
            return

        _, l_id = get_welcome_channels(member.guild.id)
        if not l_id:
            return

        channel = member.guild.get_channel(l_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        duration_str = "Unknown"
        if member.joined_at:
            delta = datetime.now(timezone.utc) - member.joined_at
            days = delta.days
            hours = delta.seconds // 3600
            if days > 0:
                duration_str = f"{days} day{'s' if days != 1 else ''}"
            else:
                duration_str = f"{hours} hour{'s' if hours != 1 else ''}"

        try:
            png_bytes = await render_leave_card(
                avatar_url=member.display_avatar.url,
                username=member.name,
                duration_str=duration_str,
                server_name=member.guild.name,
            )
            file = discord.File(io.BytesIO(png_bytes), filename="leave.png")
            await channel.send(
                content=f"**{member.name}** has left the server.",
                file=file,
            )
        except Exception as e:
            logger.error(f"Failed to send leave card in {member.guild.name}: {e}")

    @app_commands.command(name="setwelcome", description="Set the channel where visual welcome cards are sent.")
    @app_commands.describe(channel="The text channel for welcome messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.guild:
            return
        set_welcome_channel(interaction.guild.id, channel.id)
        await interaction.response.defer()
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Welcome messages will now be sent to {channel.mention} with custom visual cards.",
            ephemeral=True,
        )

    @app_commands.command(name="setleave", description="Set the channel where visual leave cards are sent.")
    @app_commands.describe(channel="The text channel for leave messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setleave(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.guild:
            return
        set_leave_channel(interaction.guild.id, channel.id)
        await interaction.response.defer()
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Leave messages will now be sent to {channel.mention} with custom visual cards.",
            ephemeral=True,
        )

    @app_commands.command(name="disablewelcome", description="Disable welcome announcements.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disablewelcome(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        set_welcome_channel(interaction.guild.id, None)
        await interaction.response.defer()
        await interaction.followup.send(f"{config.EMOJI_TICK} Welcome messages disabled.", ephemeral=True)

    @app_commands.command(name="disableleave", description="Disable leave announcements.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disableleave(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        set_leave_channel(interaction.guild.id, None)
        await interaction.response.defer()
        await interaction.followup.send(f"{config.EMOJI_TICK} Leave messages disabled.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
