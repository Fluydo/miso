from datetime import datetime, timezone
import discord
import config


def user_status_embed(member: discord.Member) -> discord.Embed:
    """Creates a comprehensive user status embed."""
    embed = discord.Embed(
        title=f"👤 User Status: {member.name}",
        color=member.top_role.color if member.top_role.color.value != 0 else config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    created_ts = int(member.created_at.timestamp())
    joined_ts = int(member.joined_at.timestamp()) if member.joined_at else None
    joined_str = f"<t:{joined_ts}:F>\n(<t:{joined_ts}:R>)" if joined_ts else "Unknown"

    status_emojis = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle",
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline",
    }
    status_str = status_emojis.get(member.status, str(member.status).title())

    embed.add_field(name="🏷️ Username", value=f"`{member.name}`", inline=True)
    embed.add_field(name="📛 Display Name", value=member.display_name, inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=True)

    embed.add_field(name="🤖 Account Type", value="`Bot`" if member.bot else "`Human`", inline=True)
    embed.add_field(name="📶 Status", value=f"`{status_str}`", inline=True)
    embed.add_field(name="👑 Top Role", value=member.top_role.mention if member.top_role else "None", inline=True)

    embed.add_field(name="📅 Account Created", value=f"<t:{created_ts}:F>\n(<t:{created_ts}:R>)", inline=True)
    embed.add_field(name="📥 Joined Server", value=joined_str, inline=True)

    roles = [role.mention for role in reversed(member.roles) if role != member.guild.default_role]
    if roles:
        roles_display = ", ".join(roles[:10])
        if len(roles) > 10:
            roles_display += f" ...and {len(roles) - 10} more"
        embed.add_field(name=f"🎭 Roles [{len(roles)}]", value=roles_display, inline=False)

    return embed
