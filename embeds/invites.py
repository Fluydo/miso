"""
embeds/invites.py
Embed builders for the invite tracking system.
Matches the visual style of the rest of Miso's embeds.
"""

from datetime import datetime, timezone
import discord
import config


def invites_embed(
    user: discord.User | discord.Member,
    stats: dict,
    guild: discord.Guild,
) -> discord.Embed:
    """
    Shows invite stats for a single user.
    stats keys: total, active, left
    """
    total = stats.get("total", 0)
    active = stats.get("active", 0)
    left = stats.get("left", 0)

    embed = discord.Embed(
        description=(
            f"{config.EMOJI_DOTSTAR} **<@{user.id}>** has invited **{total}** people\n"
            f"{config.EMOJI_CHEVRON_RIGHT} `{active}` active\n"
            f"{config.EMOJI_CHEVRON_RIGHT} `{left}` left"
        ),
        color=config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=f"{user.display_name}'s Invites", icon_url=user.display_avatar.url)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else user.display_avatar.url)
    embed.set_footer(text=f"{config.BOT_NAME} • {guild.name}")
    return embed


def invites_leaderboard_embed(
    guild: discord.Guild,
    entries: list[dict],
) -> discord.Embed:
    """
    Shows the top inviters for the server.
    entries: list of { inviter_id, total, active, left }
    """
    embed = discord.Embed(
        title=f"{config.EMOJI_DOTSTAR} Invite Leaderboard",
        color=config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"{config.BOT_NAME} • {guild.name}")

    if not entries:
        embed.description = "*No invite data recorded yet. Members need to join via tracked invites.*"
        return embed

    medals = ["🥇", "🥈", "🥉"]
    lines: list[str] = []
    for i, entry in enumerate(entries):
        prefix = medals[i] if i < 3 else f"`{i + 1}.`"
        inv_id = entry["inviter_id"]
        active = entry["active"]
        total = entry["total"]
        left = entry["left"]
        lines.append(
            f"{prefix} <@{inv_id}> — **{active}** active "
            f"(`{total}` total, `{left}` left)"
        )

    embed.description = "\n".join(lines)
    return embed


def invite_join_log_embed(
    member: discord.Member,
    inviter_id: int | None,
    invite_code: str | None,
    total_invites: int,
) -> discord.Embed:
    """
    Log embed posted to the audit log when a member joins via a tracked invite.
    """
    embed = discord.Embed(
        title=f"{config.EMOJI_MEMBER_JOIN} Member Joined via Invite",
        color=0x57F287,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name=f"{config.EMOJI_DOTSTAR} Member",
        value=f"{member.mention} (`{member.name}` | `{member.id}`)",
        inline=False,
    )

    if inviter_id:
        embed.add_field(
            name=f"{config.EMOJI_DOTSTAR} Invited By",
            value=f"<@{inviter_id}> (`{inviter_id}`) — **{total_invites}** total invites",
            inline=False,
        )
    else:
        embed.add_field(
            name=f"{config.EMOJI_DOTSTAR} Invited By",
            value="*Unknown (vanity URL, OAuth, or untracked invite)*",
            inline=False,
        )

    if invite_code:
        embed.add_field(name="Invite Code", value=f"`{invite_code}`", inline=True)

    created_ts = int(member.created_at.timestamp())
    embed.add_field(
        name="Account Age",
        value=f"<t:{created_ts}:R>",
        inline=True,
    )
    embed.set_footer(text=f"{config.BOT_NAME} Audit Logs")
    return embed
