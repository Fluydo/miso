"""
cogs/verification.py
Server Verification System for Miso Bot with Components V2 panel, auto-lockdown permissions, and visual verify logs.
"""

import io
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
from functions.moderation import send_mod_log
from functions.renderer import render_verify_log
from functions.verification import (
    add_exception_channel,
    remove_exception_channel,
    get_verification_settings,
    set_verification_setup,
)

logger = logging.getLogger("miso.cogs.verification")


class VerifyButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Verify",
            style=discord.ButtonStyle.success,
            emoji=discord.PartialEmoji.from_str(config.EMOJI_TICK),
            custom_id="miso_verify_button",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return

        settings = get_verification_settings(interaction.guild.id)
        role_id = settings.get("verified_role_id")
        if not role_id:
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Verification role has not been configured.",
                ephemeral=True,
            )
            return

        verified_role = interaction.guild.get_role(role_id)
        if not verified_role:
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Verified role not found on the server.",
                ephemeral=True,
            )
            return

        if verified_role in interaction.user.roles:
            await interaction.response.send_message(
                f"{config.EMOJI_INFO} You are already verified in **{interaction.guild.name}**!",
                ephemeral=True,
            )
            return

        try:
            await interaction.user.add_roles(verified_role, reason="Passed server verification panel")
        except discord.Forbidden:
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Failed to assign role due to bot hierarchy permissions.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"{config.EMOJI_TICK} **Successfully Verified!** Welcome to **{interaction.guild.name}**.",
            ephemeral=True,
        )

        # Log visual verification card
        try:
            png_bytes = await render_verify_log(
                user_name=str(interaction.user),
                avatar_url=interaction.user.display_avatar.url,
                verified_at_str=datetime.now(timezone.utc).strftime("%b %d, %Y at %I:%M %p UTC"),
            )
            file = discord.File(io.BytesIO(png_bytes), filename="verify_log.png")
        except Exception as e:
            logger.error(f"Error rendering verify log: {e}")
            file = None

        embed = discord.Embed(
            title=f"{config.EMOJI_TICK} Member Verified",
            description=f"{interaction.user.mention} (`{interaction.user.id}`) completed verification.",
            color=config.COLOR_SUCCESS,
        )
        if file:
            embed.set_image(url="attachment://verify_log.png")

        await send_mod_log(interaction.guild, embed, file=file, log_type="members")


class VerifyPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(VerifyButton())


class Verification(commands.Cog):
    """Server security verification and auto-lockdown permissions."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.add_view(VerifyPanelView())

    verify_group = app_commands.Group(
        name="verify",
        description="Configure server verification and permission lockdown.",
        guild_only=True,
    )

    @verify_group.command(name="setup", description="Deploy the verification panel and auto-lockdown server channels.")
    @app_commands.describe(
        channel="The channel where the verification panel will be sent",
        verified_role="The role granted upon successful verification",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        verified_role: discord.Role,
    ) -> None:
        if not interaction.guild:
            return

        await interaction.response.defer(ephemeral=True)

        set_verification_setup(interaction.guild.id, channel.id, verified_role.id)
        settings = get_verification_settings(interaction.guild.id)
        exceptions = set(settings.get("exception_channel_ids", []))

        # Auto-configure permission overwrites across all channels
        everyone_role = interaction.guild.default_role

        for ch in interaction.guild.channels:
            try:
                if ch.id == channel.id:
                    # On verification channel: @everyone can view (no chat), verified_role cannot view
                    await ch.set_permissions(
                        everyone_role,
                        view_channel=True,
                        send_messages=False,
                        add_reactions=False,
                        reason="Verification Setup",
                    )
                    await ch.set_permissions(
                        verified_role,
                        view_channel=False,
                        reason="Verification Setup",
                    )
                elif ch.id in exceptions:
                    # Exception channel: @everyone can view read-only, verified_role normal view
                    await ch.set_permissions(
                        everyone_role,
                        view_channel=True,
                        send_messages=False,
                        add_reactions=False,
                        reason="Verification Exception",
                    )
                    await ch.set_permissions(
                        verified_role,
                        view_channel=True,
                        send_messages=True,
                        reason="Verification Setup",
                    )
                else:
                    # Regular channels: @everyone cannot view, verified_role can view
                    await ch.set_permissions(
                        everyone_role,
                        view_channel=False,
                        reason="Verification Lockdown",
                    )
                    await ch.set_permissions(
                        verified_role,
                        view_channel=True,
                        reason="Verification Setup",
                    )
            except discord.Forbidden:
                continue

        # Send Verification Panel (Components V2 style)
        panel_embed = discord.Embed(
            title=f"{config.EMOJI_TICK} Server Verification",
            description=(
                f"Welcome to **{interaction.guild.name}**!\n\n"
                f"To gain access to all channels and participate in the community, "
                f"please click the **Verify** button below."
            ),
            color=config.COLOR_PRIMARY,
        )
        panel_embed.set_footer(text=f"{config.BOT_NAME} Verification • Instant Access")

        view = VerifyPanelView()
        await channel.send(embed=panel_embed, view=view)

        await interaction.followup.send(
            f"{config.EMOJI_TICK} Verification panel deployed to {channel.mention}!\n"
            f"Server permissions have been locked down for `@everyone` and unlocked for `{verified_role.name}`.",
            ephemeral=True,
        )

    exception_group = app_commands.Group(
        name="exception",
        description="Manage exception channels that unverified users can view read-only.",
        parent=verify_group,
        guild_only=True,
    )

    @exception_group.command(name="add", description="Add an exception channel for unverified users to view read-only.")
    @app_commands.describe(channel="The channel unverified users can view (e.g. #rules or #announcements)")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_exception_add(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.guild:
            return

        added = add_exception_channel(interaction.guild.id, channel.id)
        if not added:
            await interaction.response.send_message(
                f"{config.EMOJI_INFO} {channel.mention} is already an exception channel.",
                ephemeral=True,
            )
            return

        everyone_role = interaction.guild.default_role
        try:
            await channel.set_permissions(
                everyone_role,
                view_channel=True,
                send_messages=False,
                add_reactions=False,
                reason="Verification Read-Only Exception",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Missing permissions to edit channel overwrites.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"{config.EMOJI_TICK} {channel.mention} is now an exception channel — unverified users can view it read-only.",
            ephemeral=True,
        )

    @exception_group.command(name="remove", description="Remove an exception channel, locking it from unverified users again.")
    @app_commands.describe(channel="The exception channel to remove")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_exception_remove(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.guild:
            return

        removed = remove_exception_channel(interaction.guild.id, channel.id)
        if not removed:
            await interaction.response.send_message(
                f"{config.EMOJI_INFO} {channel.mention} is not in the exception list.",
                ephemeral=True,
            )
            return

        everyone_role = interaction.guild.default_role
        try:
            await channel.set_permissions(
                everyone_role,
                view_channel=False,
                reason="Verification Exception Removed",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Exception removed from config, but missing permissions to update channel overwrites.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"{config.EMOJI_TICK} {channel.mention} is no longer an exception channel — unverified users will no longer see it.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verification(bot))
