from datetime import datetime, timezone
import discord
import config


# Map of action names to their specific log emoji
_ACTION_EMOJI_MAP: dict[str, str] = {
    "Member Banned": config.EMOJI_BAN_LOGS,
    "Temporary Ban": config.EMOJI_TEMPBAN_LOGS,
    "Tempban Expired (Auto-Unban)": config.EMOJI_UNBAN_LOGS,
    "Member Kicked": config.EMOJI_KICK_LOGS,
    "Member Timed Out": config.EMOJI_TIMEOUT_LOGS,
    "Timeout Removed": config.EMOJI_UNBAN_LOGS,
    "Member Warned": config.EMOJI_WARN_LOGS,
    "Warnings Cleared": config.EMOJI_WARN_LOGS,
    "Messages Purged": config.EMOJI_MESSAGE_DELETE_LOGS,
    "Member Unbanned": config.EMOJI_UNBAN_LOGS,
}


def _base_mod_embed(title: str | None, color: int, description: str | None = None) -> discord.Embed:
    """Helper to create clean border embeds without footers or timestamps."""
    return discord.Embed(
        title=title,
        description=description,
        color=color,
    )


# ==========================================
# COMMAND CONFIRMATION RESPONSES (SLEEK STYLE)
# ==========================================

def ban_embed(moderator_id: int, user_id: int, user_name: str, reason: str) -> discord.Embed:
    description = f"{config.EMOJI_TICK} **<@{user_id}>** has been banned. Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def tempban_embed(
    moderator_id: int,
    user_id: int,
    user_name: str,
    duration: str,
    reason: str,
) -> discord.Embed:
    description = f"{config.EMOJI_TICK} **<@{user_id}>** has been temporarily banned for **{duration}**. Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def kick_embed(moderator_id: int, user_id: int, user_name: str, reason: str) -> discord.Embed:
    description = f"{config.EMOJI_TICK} **<@{user_id}>** has been kicked. Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def timeout_embed(
    moderator_id: int,
    user_id: int,
    duration: str,
    reason: str,
    user_name: str | None = None,
) -> discord.Embed:
    description = f"{config.EMOJI_TICK} **<@{user_id}>** has been timed out for **{duration}**. Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def untimeout_embed(
    moderator_id: int,
    user_id: int,
    reason: str,
    user_name: str | None = None,
) -> discord.Embed:
    description = f"{config.EMOJI_TICK} **<@{user_id}>** timeout has been removed. Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def warn_embed(
    moderator_id: int,
    user_id: int,
    reason: str,
    warning_count: int,
    user_name: str | None = None,
) -> discord.Embed:
    description = f"{config.EMOJI_WARN} **<@{user_id}>** has been warned (Warning **#{warning_count}**). Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_WARNING, description=description)


def warnings_list_embed(user_id: int, user_name: str, warnings: list[dict]) -> discord.Embed:
    embed = _base_mod_embed(
        title=f"{config.EMOJI_INFO} Warnings History for {user_name}",
        color=config.COLOR_INFO,
        description=f"**User:** <@{user_id}> (`{user_id}`)\n**Total Warnings:** `{len(warnings)}`",
    )

    if not warnings:
        embed.add_field(name="Status", value="This user has a clean record. No warnings found.", inline=False)
        return embed

    for idx, warn in enumerate(warnings, start=1):
        mod_id = warn.get("moderator_id", "Unknown")
        reason = warn.get("reason", "No reason provided")
        raw_ts = warn.get("timestamp")

        time_str = "Unknown date"
        if raw_ts:
            try:
                dt = datetime.fromisoformat(raw_ts)
                time_str = f"<t:{int(dt.timestamp())}:f>"
            except Exception:
                time_str = raw_ts

        embed.add_field(
            name=f"{config.EMOJI_WARN_LOGS} Warning #{idx}",
            value=f"**Moderator:** <@{mod_id}>\n**Date:** {time_str}\n**Reason:** {reason}",
            inline=False,
        )
    return embed


def clear_warnings_embed(
    moderator_id: int,
    user_id: int,
    cleared_count: int,
    user_name: str | None = None,
) -> discord.Embed:
    description = f"{config.EMOJI_TICK} Cleared **{cleared_count}** warning(s) for **<@{user_id}>**."
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def clear_embed(moderator_id: int, amount: int, channel_name: str) -> discord.Embed:
    description = f"{config.EMOJI_TICK} Successfully deleted **{amount}** message(s) in **#{channel_name}**."
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def unban_embed(moderator_id: int, user_id: int, user_name: str | None, reason: str) -> discord.Embed:
    description = f"{config.EMOJI_TICK} **<@{user_id}>** has been unbanned. Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def tempban_expired_embed(user_id: int, reason: str) -> discord.Embed:
    description = f"{config.EMOJI_TICK} Temporary ban expired. **<@{user_id}>** has been unbanned. Original Reason: **{reason}**"
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def dm_punishment_embed(guild_name: str, action: str, reason: str, duration: str | None = None) -> discord.Embed:
    duration_str = f" for **{duration}**" if duration else ""
    description = f"You have received a **{action}** in **{guild_name}**{duration_str}.\nReason: **{reason}**"
    return discord.Embed(
        title=None,
        description=description,
        color=config.COLOR_ERROR,
    )


def mod_log_set_embed(moderator_id: int, channel_id: int, is_forum: bool = False, threads_created: int = 0) -> discord.Embed:
    if is_forum:
        description = (
            f"{config.EMOJI_TICK} Moderation & audit logs configured to Forum <#{channel_id}>.\n"
            f"Initialized **{threads_created}** category threads (`🔨・moderation`, `💬・messages`, `👥・members`, `🏷️・profiles`, `📁・server events`)."
        )
    else:
        description = f"{config.EMOJI_TICK} Moderation action logs will now be sent to <#{channel_id}>."
    return _base_mod_embed(title=None, color=config.COLOR_SUCCESS, description=description)


def mod_log_disabled_embed(moderator_id: int) -> discord.Embed:
    description = f"{config.EMOJI_WARN} Moderation logging has been disabled for this server."
    return _base_mod_embed(title=None, color=config.COLOR_WARNING, description=description)


def mod_log_status_embed(channel_id: int | None) -> discord.Embed:
    if channel_id:
        description = f"{config.EMOJI_TICK} Current moderation log channel: <#{channel_id}>"
        return _base_mod_embed(title=None, color=config.COLOR_INFO, description=description)
    else:
        description = f"{config.EMOJI_WARN} No moderation log channel is configured. Use `/setmodlog` to set one."
        return _base_mod_embed(title=None, color=config.COLOR_WARNING, description=description)


# ==========================================
# DETAILED MOD LOG CHANNEL EMBEDS
# ==========================================

def mod_action_log_embed(
    action: str,
    moderator_id: int,
    target_id: int | None = None,
    target_name: str | None = None,
    reason: str = "No reason provided",
    channel_id: int | None = None,
    duration: str | None = None,
    extra_info: str | None = None,
    color: int = config.COLOR_ERROR,
) -> discord.Embed:
    """
    Detailed log embed sent to the configured mod log channel.
    Includes Action, Target, Moderator, Channel, Timestamp, Duration, and Reason.
    """
    action_emoji = _ACTION_EMOJI_MAP.get(action, config.EMOJI_DOTSTAR)

    embed = discord.Embed(
        title=f"{action_emoji} {action}",
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    if target_id is not None:
        target_val = f"<@{target_id}>"
        if target_name:
            target_val += f" (`{target_name}` | `{target_id}`)"
        else:
            target_val += f" (`{target_id}`)"
        embed.add_field(name=f"{config.EMOJI_DOTSTAR} Target", value=target_val, inline=False)

    embed.add_field(
        name=f"{config.EMOJI_DOTSTAR} Moderator",
        value=f"<@{moderator_id}> (`{moderator_id}`)",
        inline=True,
    )

    if channel_id:
        embed.add_field(
            name=f"{config.EMOJI_HASHTAG} Channel",
            value=f"<#{channel_id}>",
            inline=True,
        )

    current_ts = int(datetime.now(timezone.utc).timestamp())
    embed.add_field(
        name=f"{config.EMOJI_INFO} Time",
        value=f"<t:{current_ts}:F>\n(<t:{current_ts}:R>)",
        inline=True,
    )

    if duration:
        embed.add_field(name="Duration", value=f"`{duration}`", inline=True)

    if extra_info:
        embed.add_field(name="Details", value=extra_info, inline=True)

    embed.add_field(name="Reason", value=f"```{reason}```", inline=False)
    embed.set_footer(text=f"{config.BOT_NAME} Mod Logs")
    return embed
