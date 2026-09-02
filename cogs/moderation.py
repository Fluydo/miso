import io
import logging
from datetime import datetime, timezone
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from functions.permissions import can_moderate
from functions.time_parser import parse_duration, format_duration
from functions.moderation import (
    add_warning,
    get_warnings,
    clear_warnings,
    add_tempban,
    remove_tempban,
    get_expired_tempbans,
    send_mod_log,
    get_mod_log_channel_id,
    set_mod_log_channel_id,
    setup_forum_threads,
)
from functions.renderer import (
    render_moderation_action,
    render_purged_messages,
)
from embeds.moderation import (
    ban_embed,
    tempban_embed,
    kick_embed,
    timeout_embed,
    untimeout_embed,
    warn_embed,
    warnings_list_embed,
    clear_warnings_embed,
    clear_embed,
    unban_embed,
    tempban_expired_embed,
    dm_punishment_embed,
    mod_log_set_embed,
    mod_log_disabled_embed,
    mod_log_status_embed,
    mod_action_log_embed,
)
from embeds.errors import error_embed, hierarchy_error_embed

logger = logging.getLogger("miso.cogs.moderation")


class Moderation(commands.Cog):
    """Core moderation commands and server settings."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.tempban_checker.start()

    def cog_unload(self) -> None:
        self.tempban_checker.cancel()

    # ==========================================
    # BACKGROUND TEMPBAN CHECKER LOOP
    # ==========================================
    @tasks.loop(seconds=30)
    async def tempban_checker(self) -> None:
        """Background task checking and unbanning users whose tempbans expired."""
        expired_bans = get_expired_tempbans()
        for record in expired_bans:
            guild_id = record.get("guild_id")
            user_id = record.get("user_id")
            reason = record.get("reason", "Tempban expired")

            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            try:
                user = await self.bot.fetch_user(user_id)
                await guild.unban(user, reason=f"Temporary ban expired. (Original: {reason})")
                remove_tempban(guild_id, user_id)

                log_embed = mod_action_log_embed(
                    action="Tempban Expired (Auto-Unban)",
                    moderator_id=self.bot.user.id,
                    target_id=user_id,
                    target_name=str(user),
                    reason=f"Temporary ban expired. Original Reason: {reason}",
                    color=config.COLOR_SUCCESS,
                )
                await send_mod_log(guild, log_embed, log_type="moderation")
                logger.info(f"Unbanned user {user_id} from {guild.name} (tempban expired).")
            except discord.NotFound:
                remove_tempban(guild_id, user_id)
            except discord.Forbidden:
                logger.error(f"Missing permissions to unban {user_id} in {guild.name}.")
            except Exception as e:
                logger.error(f"Error handling expired tempban for {user_id} in {guild.name}: {e}")

    @tempban_checker.before_loop
    async def before_tempban_checker(self) -> None:
        await self.bot.wait_until_ready()

    # ==========================================
    # MOD LOG CONFIGURATION COMMANDS
    # ==========================================
    @app_commands.command(name="setmodlog", description="Configure the text or forum channel where logs are sent.")
    @app_commands.describe(channel="The text or forum channel to receive all audit and moderation logs")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setmodlog(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
    ) -> None:
        if not interaction.guild:
            return

        if not isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Mod log channel must be a standard Text Channel or a Forum Channel."),
                ephemeral=True,
            )
            return

        is_forum = isinstance(channel, discord.ForumChannel)
        set_mod_log_channel_id(interaction.guild.id, channel.id, is_forum=is_forum)

        forum_threads_created = False
        if is_forum:
            await interaction.response.defer(ephemeral=True)
            try:
                await setup_forum_threads(channel)
                forum_threads_created = True
            except Exception as e:
                logger.error(f"Failed to auto-create forum threads: {e}")

        embed = mod_log_set_embed(interaction.user.id, channel.id, is_forum=is_forum)
        if is_forum and forum_threads_created:
            embed.add_field(
                name=f"{config.EMOJI_TICK} Threads Created",
                value=(
                    "Created 5 dedicated audit threads:\n"
                    "`🔨・moderation` `💬・messages` `👥・members` `🏷️・profiles` `📁・server events`"
                ),
                inline=False,
            )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.defer()
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="disablemodlog", description="Disable moderation logging for this server.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disablemodlog(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        set_mod_log_channel_id(interaction.guild.id, None)
        embed = mod_log_disabled_embed(interaction.user.id)
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="modlogstatus", description="Check the currently configured mod log channel.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def modlogstatus(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        ch_id = get_mod_log_channel_id(interaction.guild.id)
        embed = mod_log_status_embed(ch_id)
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ==========================================
    # /ban
    # ==========================================
    @app_commands.command(name="ban", description="Permanently ban a member from the server.")
    @app_commands.describe(
        user="The member to ban",
        reason="The reason for the ban",
        delete_message_days="Number of days of messages to delete (0-7)",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided",
        delete_message_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        await interaction.response.defer()
        if not interaction.guild:
            return

        allowed, error_msg = can_moderate(interaction.user, user)
        if not allowed:
            await interaction.followup.send(
                embed=hierarchy_error_embed(error_msg), ephemeral=True
            )
            return

        try:
            dm_embed = dm_punishment_embed(interaction.guild.name, "Ban", reason)
            await user.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

        try:
            await interaction.guild.ban(
                user,
                reason=f"Moderator: {interaction.user} | Reason: {reason}",
                delete_message_days=delete_message_days,
            )
        except discord.Forbidden:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Failed to ban member due to missing Discord permissions."),
                ephemeral=True,
            )
            return

        embed = ban_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            user_name=str(user),
            reason=reason,
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        # Visual Moderation Card
        file = None
        try:
            png_bytes = await render_moderation_action(
                action_name="Banned",
                target_name=str(user),
                target_avatar_url=user.display_avatar.url,
                mod_name=interaction.user.name,
                reason=reason,
                badge_color="#ed4245",
            )
            file = discord.File(io.BytesIO(png_bytes), filename="mod_action.png")
        except Exception:
            pass

        log_embed = mod_action_log_embed(
            action="Member Banned",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=reason,
            channel_id=interaction.channel_id,
            color=config.COLOR_ERROR,
        )
        if file:
            log_embed.set_image(url="attachment://mod_action.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="moderation")

    # ==========================================
    # /tempban
    # ==========================================
    @app_commands.command(name="tempban", description="Temporarily ban a member from the server.")
    @app_commands.describe(
        user="The member to tempban",
        duration="Duration of ban (e.g. 10m, 1h, 2d, 7d)",
        reason="The reason for the temporary ban",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def tempban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild:
            return

        try:
            td = parse_duration(duration)
        except ValueError as e:
            await interaction.response.defer()
            await interaction.followup.send(embed=error_embed(str(e)), ephemeral=True)
            return

        allowed, error_msg = can_moderate(interaction.user, user)
        if not allowed:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=hierarchy_error_embed(error_msg), ephemeral=True
            )
            return

        formatted_duration = format_duration(td)
        unban_ts = datetime.now(timezone.utc).timestamp() + td.total_seconds()

        try:
            dm_embed = dm_punishment_embed(interaction.guild.name, "Temporary Ban", reason, formatted_duration)
            await user.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

        try:
            await interaction.guild.ban(
                user,
                reason=f"Tempban by {interaction.user} for {formatted_duration} | Reason: {reason}",
            )
        except discord.Forbidden:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Failed to ban member due to missing Discord permissions."),
                ephemeral=True,
            )
            return

        add_tempban(interaction.guild.id, user.id, unban_ts, reason)

        embed = tempban_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            user_name=str(user),
            duration=formatted_duration,
            reason=reason,
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        file = None
        try:
            png_bytes = await render_moderation_action(
                action_name="Temp Banned",
                target_name=str(user),
                target_avatar_url=user.display_avatar.url,
                mod_name=interaction.user.name,
                reason=reason,
                duration=formatted_duration,
                badge_color="#ed4245",
            )
            file = discord.File(io.BytesIO(png_bytes), filename="mod_action.png")
        except Exception:
            pass

        log_embed = mod_action_log_embed(
            action="Temporary Ban",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=reason,
            channel_id=interaction.channel_id,
            duration=formatted_duration,
            color=config.COLOR_ERROR,
        )
        if file:
            log_embed.set_image(url="attachment://mod_action.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="moderation")

    # ==========================================
    # /kick
    # ==========================================
    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(user="The member to kick", reason="The reason for kicking")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild:
            return

        allowed, error_msg = can_moderate(interaction.user, user)
        if not allowed:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=hierarchy_error_embed(error_msg), ephemeral=True
            )
            return

        try:
            dm_embed = dm_punishment_embed(interaction.guild.name, "Kick", reason)
            await user.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

        try:
            await user.kick(reason=f"Moderator: {interaction.user} | Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Failed to kick member due to missing Discord permissions."),
                ephemeral=True,
            )
            return

        embed = kick_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            user_name=str(user),
            reason=reason,
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        file = None
        try:
            png_bytes = await render_moderation_action(
                action_name="Kicked",
                target_name=str(user),
                target_avatar_url=user.display_avatar.url,
                mod_name=interaction.user.name,
                reason=reason,
                badge_color="#f59e0b",
            )
            file = discord.File(io.BytesIO(png_bytes), filename="mod_action.png")
        except Exception:
            pass

        log_embed = mod_action_log_embed(
            action="Member Kicked",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=reason,
            channel_id=interaction.channel_id,
            color=config.COLOR_ERROR,
        )
        if file:
            log_embed.set_image(url="attachment://mod_action.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="moderation")

    # ==========================================
    # /timeout
    # ==========================================
    @app_commands.command(name="timeout", description="Timeout / mute a member for a specified duration.")
    @app_commands.describe(
        user="The member to timeout",
        duration="Duration of timeout (e.g. 10m, 1h, 1d, max 28d)",
        reason="The reason for timing out the member",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild:
            return

        try:
            td = parse_duration(duration)
        except ValueError as e:
            await interaction.response.defer()
            await interaction.followup.send(embed=error_embed(str(e)), ephemeral=True)
            return

        if td.total_seconds() > 2419200:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Discord limits timeouts to a maximum of 28 days."),
                ephemeral=True,
            )
            return

        allowed, error_msg = can_moderate(interaction.user, user)
        if not allowed:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=hierarchy_error_embed(error_msg), ephemeral=True
            )
            return

        formatted_duration = format_duration(td)

        try:
            dm_embed = dm_punishment_embed(interaction.guild.name, "Timeout", reason, formatted_duration)
            await user.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

        try:
            await user.timeout(td, reason=f"Moderator: {interaction.user} | Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Failed to apply timeout due to role hierarchy or permissions."),
                ephemeral=True,
            )
            return

        embed = timeout_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            duration=formatted_duration,
            reason=reason,
            user_name=str(user),
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        file = None
        try:
            png_bytes = await render_moderation_action(
                action_name="Timed Out",
                target_name=str(user),
                target_avatar_url=user.display_avatar.url,
                mod_name=interaction.user.name,
                reason=reason,
                duration=formatted_duration,
                badge_color="#f59e0b",
            )
            file = discord.File(io.BytesIO(png_bytes), filename="mod_action.png")
        except Exception:
            pass

        log_embed = mod_action_log_embed(
            action="Member Timed Out",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=reason,
            channel_id=interaction.channel_id,
            duration=formatted_duration,
            color=config.COLOR_WARNING,
        )
        if file:
            log_embed.set_image(url="attachment://mod_action.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="moderation")

    # ==========================================
    # /untimeout
    # ==========================================
    @app_commands.command(name="untimeout", description="Remove timeout from a member.")
    @app_commands.describe(user="The member to untimeout", reason="Reason for removing the timeout")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def untimeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild:
            return

        allowed, error_msg = can_moderate(interaction.user, user)
        if not allowed:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=hierarchy_error_embed(error_msg), ephemeral=True
            )
            return

        try:
            await user.timeout(None, reason=f"Timeout removed by {interaction.user} | Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Failed to remove timeout due to permissions or hierarchy."),
                ephemeral=True,
            )
            return

        embed = untimeout_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            reason=reason,
            user_name=str(user),
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        file = None
        try:
            png_bytes = await render_moderation_action(
                action_name="Timeout Removed",
                target_name=str(user),
                target_avatar_url=user.display_avatar.url,
                mod_name=interaction.user.name,
                reason=reason,
                badge_color="#57f287",
            )
            file = discord.File(io.BytesIO(png_bytes), filename="mod_action.png")
        except Exception:
            pass

        log_embed = mod_action_log_embed(
            action="Timeout Removed",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=reason,
            channel_id=interaction.channel_id,
            color=config.COLOR_SUCCESS,
        )
        if file:
            log_embed.set_image(url="attachment://mod_action.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="moderation")

    # ==========================================
    # /warn
    # ==========================================
    @app_commands.command(name="warn", description="Issue a formal warning to a member.")
    @app_commands.describe(user="The member to warn", reason="The reason for the warning")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild:
            return

        allowed, error_msg = can_moderate(interaction.user, user)
        if not allowed:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=hierarchy_error_embed(error_msg), ephemeral=True
            )
            return

        total_count = add_warning(interaction.guild.id, user.id, interaction.user.id, reason)

        try:
            dm_embed = dm_punishment_embed(interaction.guild.name, "Warning", reason)
            await user.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

        embed = warn_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            reason=reason,
            warning_count=total_count,
            user_name=str(user),
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        file = None
        try:
            png_bytes = await render_moderation_action(
                action_name=f"Warned (#{total_count})",
                target_name=str(user),
                target_avatar_url=user.display_avatar.url,
                mod_name=interaction.user.name,
                reason=reason,
                badge_color="#f59e0b",
            )
            file = discord.File(io.BytesIO(png_bytes), filename="mod_action.png")
        except Exception:
            pass

        log_embed = mod_action_log_embed(
            action="Member Warned",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=reason,
            channel_id=interaction.channel_id,
            extra_info=f"Total Warnings: `{total_count}`",
            color=config.COLOR_WARNING,
        )
        if file:
            log_embed.set_image(url="attachment://mod_action.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="moderation")

    # ==========================================
    # /warnings
    # ==========================================
    @app_commands.command(name="warnings", description="View warning history for a user.")
    @app_commands.describe(user="The member to check warnings for")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        user: discord.User,
    ) -> None:
        if not interaction.guild:
            return

        user_warns = get_warnings(interaction.guild.id, user.id)
        embed = warnings_list_embed(
            user_id=user.id,
            user_name=str(user),
            warnings=user_warns,
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

    # ==========================================
    # /clearwarnings
    # ==========================================
    @app_commands.command(name="clearwarnings", description="Clear all warnings for a user.")
    @app_commands.describe(user="The member whose warnings will be wiped")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clearwarnings(
        self,
        interaction: discord.Interaction,
        user: discord.User,
    ) -> None:
        if not interaction.guild:
            return

        cleared = clear_warnings(interaction.guild.id, user.id)
        embed = clear_warnings_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            cleared_count=cleared,
            user_name=str(user),
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        log_embed = mod_action_log_embed(
            action="Warnings Cleared",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=f"Cleared {cleared} warning(s)",
            channel_id=interaction.channel_id,
            color=config.COLOR_SUCCESS,
        )
        await send_mod_log(interaction.guild, log_embed, log_type="moderation")

    # ==========================================
    # /clear
    # ==========================================
    @app_commands.command(name="clear", description="Bulk delete messages from the current channel.")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ) -> None:
        if not interaction.guild:
            return

        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
            await interaction.followup.send(
                embed=error_embed("Messages cannot be cleared in this type of channel."),
                ephemeral=True,
            )
            return

        try:
            deleted = await channel.purge(limit=amount)
            count = len(deleted)
        except discord.HTTPException as e:
            await interaction.followup.send(
                embed=error_embed(f"Failed to clear messages: {e}"),
                ephemeral=True,
            )
            return

        embed = clear_embed(
            moderator_id=interaction.user.id,
            amount=count,
            channel_name=channel.name,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

        # Render visual message transcript if <= 15 messages
        file = None
        if deleted and len(deleted) <= 15:
            try:
                msg_list = []
                for m in reversed(deleted):
                    replied_to = None
                    if m.reference and m.reference.resolved and isinstance(m.reference.resolved, discord.Message):
                        ref = m.reference.resolved
                        replied_to = {
                            "author_name": getattr(ref.author, "display_name", ref.author.name),
                            "avatar_url": ref.author.display_avatar.url,
                            "content": ref.content[:50] if ref.content else "[Attachment/Embed]",
                        }
                    msg_list.append({
                        "author_name": getattr(m.author, "display_name", m.author.name),
                        "avatar_url": m.author.display_avatar.url,
                        "content": m.content,
                        "timestamp_str": m.created_at.strftime("Today at %I:%M %p"),
                        "is_bot": m.author.bot,
                        "replied_to": replied_to,
                    })
                png_bytes = await render_purged_messages(msg_list)
                file = discord.File(io.BytesIO(png_bytes), filename="purged_messages.png")
            except Exception as e:
                logger.error(f"Error rendering purged messages: {e}")

        log_embed = mod_action_log_embed(
            action="Messages Purged",
            moderator_id=interaction.user.id,
            reason=f"Purged {count} messages in #{channel.name}",
            channel_id=channel.id,
            extra_info=f"Amount: `{count}` messages",
            color=config.COLOR_SUCCESS,
        )
        if file:
            log_embed.set_image(url="attachment://purged_messages.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="messages")

    # ==========================================
    # /unban
    # ==========================================
    @app_commands.command(name="unban", description="Unban a user by their Discord User ID.")
    @app_commands.describe(user_id="The Discord ID of the user to unban", reason="Reason for unbanning")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild:
            return

        if not user_id.strip().isdigit():
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Invalid User ID. Please provide a numeric Discord User ID."),
                ephemeral=True,
            )
            return

        target_id = int(user_id.strip())

        try:
            user = await self.bot.fetch_user(target_id)
        except discord.NotFound:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Could not find a Discord user with that ID."),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Failed to retrieve user information from Discord."),
                ephemeral=True,
            )
            return

        try:
            await interaction.guild.unban(
                user,
                reason=f"Unbanned by {interaction.user} | Reason: {reason}",
            )
        except discord.NotFound:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed(f"**{user}** (`{user.id}`) is not currently banned in this server."),
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Failed to unban user due to missing Discord permissions."),
                ephemeral=True,
            )
            return

        remove_tempban(interaction.guild.id, target_id)

        embed = unban_embed(
            moderator_id=interaction.user.id,
            user_id=user.id,
            user_name=str(user),
            reason=reason,
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

        file = None
        try:
            png_bytes = await render_moderation_action(
                action_name="Unbanned",
                target_name=str(user),
                target_avatar_url=user.display_avatar.url,
                mod_name=interaction.user.name,
                reason=reason,
                badge_color="#57f287",
            )
            file = discord.File(io.BytesIO(png_bytes), filename="mod_action.png")
        except Exception:
            pass

        log_embed = mod_action_log_embed(
            action="Member Unbanned",
            moderator_id=interaction.user.id,
            target_id=user.id,
            target_name=str(user),
            reason=reason,
            channel_id=interaction.channel_id,
            color=config.COLOR_SUCCESS,
        )
        if file:
            log_embed.set_image(url="attachment://mod_action.png")
        await send_mod_log(interaction.guild, log_embed, file=file, log_type="moderation")

    # ==========================================
    # /slowmode
    # ==========================================
    @app_commands.command(name="slowmode", description="Set or remove slowmode on a channel.")
    @app_commands.describe(
        seconds="Slowmode delay in seconds (0 = off, max 21600 / 6 hours)",
        channel="Channel to apply slowmode to (defaults to current channel)",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        if not interaction.guild:
            return

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Slowmode can only be set on text channels."),
                ephemeral=True,
            )
            return

        try:
            await target.edit(slowmode_delay=seconds)
        except discord.Forbidden:
            await interaction.response.defer()
            await interaction.followup.send(
                embed=error_embed("Missing permissions to edit that channel."),
                ephemeral=True,
            )
            return

        if seconds == 0:
            desc = f"{config.EMOJI_TICK} Slowmode **disabled** in {target.mention}."
        else:
            # Format a human-readable duration
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            parts = []
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if secs:
                parts.append(f"{secs}s")
            duration = " ".join(parts)
            desc = (
                f"{config.EMOJI_TICK} Slowmode set to **{duration}** in {target.mention}.\n"
                f"Users must wait `{duration}` between messages."
            )

        embed = discord.Embed(description=desc, color=config.COLOR_SUCCESS)
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, ephemeral=True)

        log_embed = mod_action_log_embed(
            action="Slowmode Updated",
            moderator_id=interaction.user.id,
            reason=f"{'Disabled' if seconds == 0 else f'Set to {seconds}s'} in #{target.name}",
            channel_id=target.id,
            extra_info=f"Delay: `{seconds}s`",
            color=config.COLOR_INFO,
        )
        await send_mod_log(interaction.guild, log_embed, log_type="server")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
