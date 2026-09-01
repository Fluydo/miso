import platform
from datetime import datetime, timezone
import discord
from discord.ui import Container, Section, TextDisplay, Thumbnail, MediaGallery, Separator, Button, ActionRow, LayoutView
import config

SERVER_INFO_COLOR: int = 0xA240F7


def ping_embed(latency_ms: float) -> discord.Embed:
    """Embed showing websocket and response latency."""
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Bot Latency:** `{latency_ms:.2f}ms`",
        color=config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"{config.BOT_NAME} Utility")
    return embed


def avatar_embed(user: discord.User | discord.Member) -> discord.Embed:
    """Embed showcasing a user's high-res avatar."""
    embed = discord.Embed(
        title=f"🖼️ Avatar for {user.display_name}",
        color=config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_image(url=user.display_avatar.url)
    embed.description = f"[Direct Image Link]({user.display_avatar.url})"
    embed.set_footer(text=f"{config.BOT_NAME} Utility • User ID: {user.id}")
    return embed


def user_info_embed(member: discord.Member) -> discord.Embed:
    """Detailed user information embed."""
    embed = discord.Embed(
        title=f"ℹ️ User Information: {member.name}",
        color=member.top_role.color if member.top_role.color.value != 0 else config.COLOR_INFO,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    created_ts = int(member.created_at.timestamp())
    joined_ts = int(member.joined_at.timestamp()) if member.joined_at else None

    embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="Account Type", value="`Bot`" if member.bot else "`Human`", inline=True)
    embed.add_field(name="Top Role", value=member.top_role.mention if member.top_role else "None", inline=True)

    embed.add_field(name="Registered", value=f"<t:{created_ts}:D>\n(<t:{created_ts}:R>)", inline=True)
    if joined_ts:
        embed.add_field(name="Joined Server", value=f"<t:{joined_ts}:D>\n(<t:{joined_ts}:R>)", inline=True)

    key_perms = []
    if member.guild_permissions.administrator:
        key_perms.append("Administrator")
    if member.guild_permissions.manage_guild:
        key_perms.append("Manage Server")
    if member.guild_permissions.ban_members:
        key_perms.append("Ban Members")
    if member.guild_permissions.kick_members:
        key_perms.append("Kick Members")
    if member.guild_permissions.manage_messages:
        key_perms.append("Manage Messages")

    if key_perms:
        embed.add_field(name="Key Permissions", value=", ".join(key_perms), inline=False)

    roles = [role.mention for role in reversed(member.roles) if role != member.guild.default_role]
    if roles:
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:15]), inline=False)

    embed.set_footer(text=f"{config.BOT_NAME} Utility")
    return embed


def server_roles_embed(guild: discord.Guild) -> discord.Embed:
    """
    Standard ephemeral roles list embed with #a240f7 hex color.
    """
    roles = [role.mention for role in reversed(guild.roles) if role != guild.default_role]
    total_count = len(roles)

    if not roles:
        description = "No custom roles found."
    else:
        full_text = "\n".join(roles)
        if len(full_text) > 4000:
            description = full_text[:3980] + "\n...and more"
        else:
            description = full_text

    return discord.Embed(
        title=f"Roles [{total_count}]",
        description=description,
        color=SERVER_INFO_COLOR,
    )


def create_server_info_view(guild: discord.Guild) -> LayoutView:
    """
    Constructs the Discord Components V2 LayoutView for /serverinfo.
    Uses Container (accent color #a240f7), Section with Thumbnail accessory,
    Separators, MediaGallery for banner, and an ActionRow wrapping the View Roles button.
    """
    view = LayoutView(timeout=180)
    created_ts = int(guild.created_at.timestamp())

    # Header block
    header_text = (
        f"## {guild.name}\n"
        f"**Owner:** <@{guild.owner_id}>\n"
        f"**Members:** `{guild.member_count or len(guild.members)}`\n"
        f"**Roles:** `{len(guild.roles)}`"
    )

    container_items = []

    # Section with server icon thumbnail on the right side
    if guild.icon:
        container_items.append(Section(TextDisplay(header_text), accessory=Thumbnail(guild.icon.url)))
    else:
        container_items.append(TextDisplay(header_text))

    # Small divider 1
    container_items.append(Separator(spacing=discord.SeparatorSpacing.small))

    # Channels block
    channels_text = (
        f"**Category Channels:** `{len(guild.categories)}`\n"
        f"**Text Channels:** `{len(guild.text_channels)}`\n"
        f"**Voice Channels:** `{len(guild.voice_channels)}`"
    )
    container_items.append(TextDisplay(channels_text))

    # Small divider 2
    container_items.append(Separator(spacing=discord.SeparatorSpacing.small))

    # Boost block
    boost_text = f"**Boost Count:** `{guild.premium_subscription_count or 0}` (Tier {guild.premium_tier})"
    container_items.append(TextDisplay(boost_text))

    # Banner image media gallery if server has a banner
    if guild.banner:
        container_items.append(MediaGallery(discord.MediaGalleryItem(guild.banner.url)))

    # Big divider 3
    container_items.append(Separator(spacing=discord.SeparatorSpacing.large))

    # Metadata footer block
    footer_text = (
        f"-# ID: {guild.id}\n"
        f"-# Server Created: <t:{created_ts}:F> (<t:{created_ts}:R>)"
    )
    container_items.append(TextDisplay(footer_text))

    # Create the Container Component with accent color #a240f7
    container = Container(*container_items, accent_color=discord.Color(SERVER_INFO_COLOR))
    view.add_item(container)

    # Wrap the secondary button in an ActionRow component (type 1)
    async def on_view_roles(interaction: discord.Interaction) -> None:
        target_guild = interaction.guild or guild
        roles_embed = server_roles_embed(target_guild)
        await interaction.response.send_message(embed=roles_embed, ephemeral=True)

    btn = Button(label="View Roles", style=discord.ButtonStyle.secondary)
    btn.callback = on_view_roles
    view.add_item(ActionRow(btn))

    return view


def bot_info_embed(bot: discord.Client, uptime_seconds: float) -> discord.Embed:
    """Embed showcasing bot status, statistics, and system environment."""
    embed = discord.Embed(
        title=f"🤖 About {config.BOT_NAME}",
        description=config.BOT_DESCRIPTION,
        color=config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

    total_guilds = len(bot.guilds)
    total_users = sum(g.member_count or len(g.members) for g in bot.guilds)

    embed.add_field(name="Version", value=f"`v{config.BOT_VERSION}`", inline=True)
    embed.add_field(name="discord.py", value=f"`v{discord.__version__}`", inline=True)
    embed.add_field(name="Python", value=f"`v{platform.python_version()}`", inline=True)

    embed.add_field(name="Guilds", value=f"`{total_guilds}`", inline=True)
    embed.add_field(name="Users Cached", value=f"`{total_users}`", inline=True)
    embed.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)

    embed.set_footer(text=f"{config.BOT_NAME} Information")
    return embed


def create_embed(
    title: str = "",
    description: str = "",
    color: discord.Color = None
) -> discord.Embed:
    """Simple helper to create a basic embed with title, description, and optional color."""
    if color is None:
        color = config.COLOR_PRIMARY
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    return embed
