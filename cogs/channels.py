"""
cogs/channels.py
Channel behaviour management commands for Miso Bot.

Features:
- /imagechannel add/remove  — Designate channels as image-only; non-image messages are auto-deleted.
- /counting set             — Set a counting channel and reset the count.
- /counting toggle          — Enable or disable counting enforcement.
- on_message listener       — Enforces both image-only and counting rules.
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from functions.moderation import (
    add_image_channel,
    remove_image_channel,
    get_image_channels,
    get_counting_config,
    set_counting_channel,
    set_counting_enabled,
    update_counting_state,
    reset_counting,
)

logger = logging.getLogger("miso.cogs.channels")

# ─── helpers ─────────────────────────────────────────────────────────────────

def _has_image(message: discord.Message) -> bool:
    """True if the message contains at least one image attachment or image embed."""
    for att in message.attachments:
        if att.content_type and att.content_type.startswith("image/"):
            return True
    for embed in message.embeds:
        if embed.type == "image":
            return True
        if embed.image:
            return True
    return False


# ─── cog ─────────────────────────────────────────────────────────────────────

class Channels(commands.Cog):
    """Image-only channels and counting channel management."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # =========================================================================
    # on_message — image-only + counting enforcement
    # =========================================================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        channel_id = message.channel.id

        # ── image-only enforcement ────────────────────────────────────────────
        image_channels = get_image_channels(guild_id)
        if channel_id in image_channels:
            if not _has_image(message):
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                try:
                    notice = await message.channel.send(
                        f"{config.EMOJI_CROSS} {message.author.mention} — "
                        f"this channel only accepts image posts.",
                        delete_after=6,
                    )
                except discord.Forbidden:
                    pass
                return  # no point checking counting for deleted message

        # ── counting enforcement ──────────────────────────────────────────────
        cfg = get_counting_config(guild_id)
        if cfg.get("enabled") and cfg.get("channel_id") == channel_id:
            content = message.content.strip()

            # Must be a plain integer, nothing else
            try:
                number = int(content)
            except ValueError:
                # Not a number — delete silently
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                try:
                    await message.channel.send(
                        f"{config.EMOJI_CROSS} {message.author.mention} — "
                        f"only numbers are allowed in this channel.",
                        delete_after=6,
                    )
                except discord.Forbidden:
                    pass
                return

            last_number = cfg.get("last_number", 0)
            last_user_id = cfg.get("last_user_id")
            expected = last_number + 1

            # Same person counting twice in a row
            if message.author.id == last_user_id:
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                reset_counting(guild_id)
                try:
                    await message.channel.send(
                        f"💥 {message.author.mention} counted twice in a row! "
                        f"Count reset back to **0**.",
                        delete_after=10,
                    )
                except discord.Forbidden:
                    pass
                return

            # Wrong number
            if number != expected:
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                reset_counting(guild_id)
                try:
                    await message.channel.send(
                        f"💥 {message.author.mention} ruined the count at **{last_number}**! "
                        f"The next number was `{expected}`. Count reset to **0**.",
                        delete_after=10,
                    )
                except discord.Forbidden:
                    pass
                return

            # Correct — advance count and react
            update_counting_state(guild_id, number, message.author.id)
            try:
                await message.add_reaction("✅")
            except (discord.Forbidden, discord.NotFound):
                pass

    # =========================================================================
    # /imagechannel group
    # =========================================================================
    imagechannel_group = app_commands.Group(
        name="imagechannel",
        description="Manage image-only channels.",
        guild_only=True,
    )

    @imagechannel_group.command(
        name="add",
        description="Make a channel image-only — non-image messages are auto-deleted.",
    )
    @app_commands.describe(channel="The channel to restrict to images only (defaults to current channel)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def imagechannel_add(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Image-only mode can only be set on text channels.",
                ephemeral=True,
            )
            return

        added = add_image_channel(interaction.guild_id, target.id)
        if not added:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_INFO} {target.mention} is already an image-only channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await interaction.followup.send(
            f"{config.EMOJI_TICK} {target.mention} is now **image-only** — "
            f"any message without an image will be automatically deleted.",
            ephemeral=True,
        )
        logger.info(f"[{interaction.guild}] Image-only enabled for #{target.name} by {interaction.user}")

    @imagechannel_group.command(
        name="remove",
        description="Remove image-only restriction from a channel.",
    )
    @app_commands.describe(channel="The channel to unrestrict (defaults to current channel)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def imagechannel_remove(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} This command only applies to text channels.",
                ephemeral=True,
            )
            return

        removed = remove_image_channel(interaction.guild_id, target.id)
        if not removed:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_INFO} {target.mention} is not an image-only channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Removed image-only restriction from {target.mention}.",
            ephemeral=True,
        )
        logger.info(f"[{interaction.guild}] Image-only removed for #{target.name} by {interaction.user}")

    # =========================================================================
    # /counting group
    # =========================================================================
    counting_group = app_commands.Group(
        name="counting",
        description="Manage the server counting channel.",
        guild_only=True,
    )

    @counting_group.command(
        name="set",
        description="Set (or change) the counting channel and reset the count to 0.",
    )
    @app_commands.describe(channel="The channel to use for counting (defaults to current channel)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def counting_set(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} The counting channel must be a text channel.",
                ephemeral=True,
            )
            return

        set_counting_channel(interaction.guild_id, target.id)

        await interaction.response.defer()
        await interaction.followup.send(
            f"{config.EMOJI_TICK} {target.mention} is now the **counting channel**.\n"
            f"Count starts at `1` — only sequential numbers are allowed, "
            f"and the same person cannot count twice in a row.",
            ephemeral=True,
        )

        # Post a start message in the channel itself
        try:
            await target.send(
                f"🔢 **Counting starts here!** Begin from `1` — "
                f"only one number per turn, and you can't count twice in a row."
            )
        except discord.Forbidden:
            pass

        logger.info(f"[{interaction.guild}] Counting channel set to #{target.name} by {interaction.user}")

    @counting_group.command(
        name="toggle",
        description="Enable or disable counting enforcement without changing the channel or resetting the count.",
    )
    @app_commands.describe(enabled="True to enable counting, False to disable")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def counting_toggle(
        self,
        interaction: discord.Interaction,
        enabled: bool,
    ) -> None:
        cfg = get_counting_config(interaction.guild_id)
        if not cfg.get("channel_id"):
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} No counting channel is set. Use `/counting set` first.",
                ephemeral=True,
            )
            return

        set_counting_enabled(interaction.guild_id, enabled)

        ch = interaction.guild.get_channel(cfg["channel_id"])
        ch_mention = ch.mention if ch else f"`{cfg['channel_id']}`"
        status = "enabled" if enabled else "disabled"
        emoji = config.EMOJI_TICK if enabled else config.EMOJI_WARN

        await interaction.response.defer()
        await interaction.followup.send(
            f"{emoji} Counting in {ch_mention} is now **{status}**.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Channels(bot))
