"""
cogs/antinuke.py
Anti-Nuke Protection Cog for Miso Bot.

Monitors rapid administrative actions:
- Channel deletions / creations
- Role deletions / creations
- Mass bans / kicks

When triggered:
- Immediately strips dangerous roles from the rogue moderator.
- Sends visual Anti-Nuke alert card to the audit logs.
"""

import io
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from functions.antinuke import (
    get_antinuke_settings,
    is_antinuke_enabled,
    record_and_check_violation,
    set_antinuke_enabled,
    set_antinuke_threshold,
)
from functions.moderation import send_mod_log
from functions.renderer import render_antinuke_trigger

logger = logging.getLogger("miso.cogs.antinuke")

# Permissions deemed dangerous in a nuke scenario
DANGEROUS_PERMS = [
    "administrator",
    "manage_guild",
    "manage_channels",
    "manage_roles",
    "ban_members",
    "kick_members",
    "manage_webhooks",
    "mention_everyone",
]


class AntiNuke(commands.Cog):
    """Real-time protection against rogue staff & server nukers."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _handle_trigger(self, guild: discord.Guild, mod: discord.Member, action_type: str, count: int, threshold: int) -> None:
        """Quarantines the moderator by stripping dangerous roles and sending visual alerts."""
        if mod.id == guild.owner_id or mod.id == self.bot.user.id:
            return

        stripped_roles = []
        roles_to_remove = []

        for role in mod.roles:
            if role.is_default():
                continue
            # Check if role has any dangerous permissions
            has_dangerous = any(getattr(role.permissions, p, False) for p in DANGEROUS_PERMS)
            if has_dangerous and role < guild.me.top_role:
                roles_to_remove.append(role)
                stripped_roles.append(role.name)

        if roles_to_remove:
            try:
                await mod.remove_roles(*roles_to_remove, reason=f"ANTI-NUKE TRIGGER: Rapid {action_type} ({count}/{threshold} in 10s)")
            except discord.Forbidden:
                logger.error(f"Failed to strip roles from {mod} during anti-nuke trigger in {guild.name}.")

        try:
            png_bytes = await render_antinuke_trigger(
                mod_name=str(mod),
                mod_avatar_url=mod.display_avatar.url,
                action_type=action_type,
                count=count,
                threshold=threshold,
            )
            file = discord.File(io.BytesIO(png_bytes), filename="antinuke_quarantine.png")
        except Exception as e:
            logger.error(f"Error rendering antinuke trigger: {e}")
            file = None

        embed = discord.Embed(
            title="🚨 ANTI-NUKE PROTECTION TRIGGERED!",
            description=(
                f"**Perpetrator:** {mod.mention} (`{mod.id}`)\n"
                f"**Trigger:** Rapid **{action_type}** (`{count}/{threshold}` actions in 10s)\n"
                f"**Action Taken:** Stripped `{len(stripped_roles)}` dangerous role(s).\n"
                f"**Roles Stripped:** {', '.join([f'`{r}`' for r in stripped_roles]) if stripped_roles else '*None (Role hierarchy)*'}"
            ),
            color=config.COLOR_ERROR,
        )
        if file:
            embed.set_image(url="attachment://antinuke_quarantine.png")

        await send_mod_log(guild, embed, file=file, log_type="moderation")

    # ==========================================
    # EVENT AUDIT MONITORS
    # ==========================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        guild = channel.guild
        if not is_antinuke_enabled(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.user and isinstance(entry.user, discord.Member):
                    violated, count, thresh = record_and_check_violation(guild.id, entry.user.id, "Channel Deletions")
                    if violated:
                        await self._handle_trigger(guild, entry.user, "Channel Deletions", count, thresh)
                break
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        guild = role.guild
        if not is_antinuke_enabled(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.user and isinstance(entry.user, discord.Member):
                    violated, count, thresh = record_and_check_violation(guild.id, entry.user.id, "Role Deletions")
                    if violated:
                        await self._handle_trigger(guild, entry.user, "Role Deletions", count, thresh)
                break
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member) -> None:
        if not is_antinuke_enabled(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.user and isinstance(entry.user, discord.Member):
                    violated, count, thresh = record_and_check_violation(guild.id, entry.user.id, "Mass Bans")
                    if violated:
                        await self._handle_trigger(guild, entry.user, "Mass Bans", count, thresh)
                break
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        guild = member.guild
        if not is_antinuke_enabled(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target and entry.target.id == member.id and entry.user and isinstance(entry.user, discord.Member):
                    violated, count, thresh = record_and_check_violation(guild.id, entry.user.id, "Mass Kicks")
                    if violated:
                        await self._handle_trigger(guild, entry.user, "Mass Kicks", count, thresh)
                break
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ==========================================
    # SLASH COMMANDS
    # ==========================================
    antinuke_group = app_commands.Group(
        name="antinuke",
        description="Anti-Nuke protection and rogue staff quarantine system.",
        guild_only=True,
    )

    @antinuke_group.command(name="status", description="Check Anti-Nuke system status and threshold settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def antinuke_status(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        settings = get_antinuke_settings(interaction.guild.id)
        status_str = f"{config.EMOJI_TICK} **Enabled**" if settings.get("enabled") else f"{config.EMOJI_CROSS} **Disabled**"

        embed = discord.Embed(
            title="🛡️ Anti-Nuke Protection Status",
            description=(
                f"**Status:** {status_str}\n"
                f"**Threshold:** `{settings.get('threshold', 3)}` dangerous actions in `{settings.get('window_seconds', 10)}` seconds\n"
                f"**Monitored Events:** Channel deletes, role deletes, mass bans, mass kicks\n"
                f"**Quarantine Action:** Immediately strips administrative permissions and sends visual alert."
            ),
            color=config.COLOR_PRIMARY,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @antinuke_group.command(name="enable", description="Enable Anti-Nuke protection on this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def antinuke_enable(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        set_antinuke_enabled(interaction.guild.id, True)
        await interaction.response.send_message(f"{config.EMOJI_TICK} Anti-Nuke protection has been **enabled**.", ephemeral=True)

    @antinuke_group.command(name="disable", description="Disable Anti-Nuke protection on this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def antinuke_disable(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        set_antinuke_enabled(interaction.guild.id, False)
        await interaction.response.send_message(f"{config.EMOJI_WARN} Anti-Nuke protection has been **disabled**.", ephemeral=True)

    @antinuke_group.command(name="setlimit", description="Set the action count threshold before quarantine.")
    @app_commands.describe(limit="Number of rapid actions allowed in 10s (minimum 2)")
    @app_commands.checks.has_permissions(administrator=True)
    async def antinuke_setlimit(self, interaction: discord.Interaction, limit: int) -> None:
        if not interaction.guild:
            return
        if limit < 2:
            await interaction.response.send_message(f"{config.EMOJI_CROSS} Minimum limit is **2** actions.", ephemeral=True)
            return
        set_antinuke_threshold(interaction.guild.id, limit)
        await interaction.response.send_message(f"{config.EMOJI_TICK} Anti-Nuke threshold updated to **{limit}** actions in 10s.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntiNuke(bot))
