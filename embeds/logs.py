import io
from datetime import datetime, timezone
import discord
from discord.ui import LayoutView, Container, TextDisplay, MediaGallery, Separator

import config
from functions.renderer import (
    render_deleted_message,
    render_edited_message,
    render_avatar_change,
    render_name_change,
    render_channel_pill,
    render_channel_update,
    render_role_pill,
    render_role_update,
    render_role_permissions_update,
    render_server_update,
)


def _base_log_embed(title: str, color: int) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"{config.BOT_NAME} Audit Logs")
    return embed


LOG_COLOR_BLUE: int = 0x5865F2    # Info / Join / Role changes
LOG_COLOR_GREEN: int = 0x57F287   # Created / Success
LOG_COLOR_RED: int = 0xED4245     # Deleted / Leave
LOG_COLOR_YELLOW: int = 0xFEE75C  # Edited / Updated


def _get_clan_info(user: discord.User | discord.Member) -> tuple[str | None, str | None]:
    """Extracts clan tag and badge url from member/user primary guild if available."""
    primary_guild = getattr(user, "primary_guild", None)
    if not primary_guild:
        return None, None
    tag = getattr(primary_guild, "tag", None)
    badge = getattr(primary_guild, "badge", None)
    badge_url = getattr(badge, "url", str(badge)) if badge else None
    return tag, badge_url


def _get_channel_type_key(channel: discord.abc.GuildChannel) -> str:
    """Maps discord channel type to SVG icon key."""
    if isinstance(channel, discord.VoiceChannel):
        return "voice"
    elif isinstance(channel, discord.ForumChannel):
        return "forum"
    elif isinstance(channel, discord.CategoryChannel):
        return "category"
    elif getattr(channel, "is_news", lambda: False)():
        return "announcement"
    return "text"


# ==========================================
# COMPONENTS V2 VISUAL LOG VIEWS (WITH IMAGES)
# ==========================================

async def create_message_delete_log_view(
    message: discord.Message,
) -> tuple[LayoutView, discord.File]:
    """Generates a Discord Components V2 log container with a rendered Discord UI message card."""
    author = message.author
    avatar_url = author.display_avatar.url
    author_name = getattr(author, "display_name", author.name)
    clan_tag, clan_badge_url = _get_clan_info(author)
    created_str = message.created_at.strftime("Today at %I:%M %p")

    # Build content description
    content_parts = []
    if message.content:
        content_parts.append(message.content)
    if message.embeds:
        content_parts.append(f"[{len(message.embeds)} embed(s)]")
    if message.attachments:
        content_parts.append(f"[{len(message.attachments)} attachment(s)]")
    if message.components:
        content_parts.append("[Components V2]")
    
    display_content = " ".join(content_parts) if content_parts else "No text content"

    png_bytes = await render_deleted_message(
        author_name=author_name,
        avatar_url=avatar_url,
        content=display_content,
        clan_tag=clan_tag,
        clan_badge_url=clan_badge_url,
        timestamp_str=created_str,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="deleted_message.png")

    item = discord.MediaGalleryItem("attachment://deleted_message.png")
    gallery = MediaGallery(item)

    # Build detailed header
    embed_info = ""
    if message.embeds:
        embed_titles = []
        for i, embed in enumerate(message.embeds[:3], 1):  # Show first 3 embeds
            title = embed.title or embed.description[:50] if embed.description else f"Embed {i}"
            embed_titles.append(f"  {i}. {title}")
        embed_info = f"\n**Embeds ({len(message.embeds)}):**\n" + "\n".join(embed_titles)
        if len(message.embeds) > 3:
            embed_info += f"\n  ... and {len(message.embeds) - 3} more"
    
    attachment_info = ""
    if message.attachments:
        attachment_info = f"\n**Attachments:** {', '.join([att.filename for att in message.attachments[:5]])}"
        if len(message.attachments) > 5:
            attachment_info += f" ... and {len(message.attachments) - 5} more"

    header_text = (
        f"### {config.EMOJI_MESSAGE_DELETE_LOGS} Message Deleted\n"
        f"**Author:** {author.mention} (`{author.name}` | `{author.id}`)\n"
        f"**Channel:** {message.channel.mention} (`#{message.channel.name}`)"
        f"{embed_info}{attachment_info}"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Message ID: `{message.id}`"),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_message_edit_log_view(
    before: discord.Message,
    after: discord.Message,
) -> tuple[LayoutView, discord.File]:
    """Generates a Discord Components V2 log container comparing before and after message cards."""
    author = before.author
    avatar_url = author.display_avatar.url
    author_name = getattr(author, "display_name", author.name)
    clan_tag, clan_badge_url = _get_clan_info(author)
    created_str = before.created_at.strftime("Today at %I:%M %p")

    png_bytes = await render_edited_message(
        author_name=author_name,
        avatar_url=avatar_url,
        before_content=before.content or "",
        after_content=after.content or "",
        clan_tag=clan_tag,
        clan_badge_url=clan_badge_url,
        timestamp_str=created_str,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="edited_message.png")

    item = discord.MediaGalleryItem("attachment://edited_message.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_MESSAGE_EDIT_LOGS} Message Edited\n"
        f"**Author:** {author.mention} (`{author.name}` | `{author.id}`)\n"
        f"**Channel:** {before.channel.mention} ➔ [Jump to Message]({after.jump_url})"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Message ID: `{before.id}`"),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_avatar_update_log_view(
    user: discord.User | discord.Member,
    before_url: str,
    after_url: str,
) -> tuple[LayoutView, discord.File]:
    """Generates a Discord Components V2 log container with before and after rounded square profile avatars."""
    png_bytes = await render_avatar_change(
        before_avatar_url=before_url,
        after_avatar_url=after_url,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="avatar_change.png")

    item = discord.MediaGalleryItem("attachment://avatar_change.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_PFP} Profile Avatar Updated\n"
        f"**User:** {user.mention} (`{user.name}` | `{user.id}`)"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# User ID: `{user.id}`"),
        accent_color=discord.Color.from_rgb(162, 64, 247),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_name_update_log_view(
    user: discord.User | discord.Member,
    before_name: str,
    after_name: str,
    is_nick: bool = False,
) -> tuple[LayoutView, discord.File]:
    """Generates a Discord Components V2 log container for nickname/username change with visual comparison."""
    title = "Nickname Updated" if is_nick else "Username Updated"
    avatar_url = user.display_avatar.url

    png_bytes = await render_name_change(
        avatar_url=avatar_url,
        before_name=before_name,
        after_name=after_name,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="name_change.png")

    item = discord.MediaGalleryItem("attachment://name_change.png")
    gallery = MediaGallery(item)

    emoji = config.EMOJI_NAME
    header_text = (
        f"### {emoji} {title}\n"
        f"**User:** {user.mention} (`{user.name}` | `{user.id}`)"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# User ID: `{user.id}`"),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_channel_create_log_view(
    channel: discord.abc.GuildChannel,
) -> tuple[LayoutView, discord.File]:
    """Generates visual log for channel creation (single Discord channel pill)."""
    type_key = _get_channel_type_key(channel)
    png_bytes = await render_channel_pill(
        channel_name=channel.name,
        channel_type=type_key,
        is_deleted=False,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="channel_create.png")

    item = discord.MediaGalleryItem("attachment://channel_create.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_HASHTAG} Channel Created\n"
        f"**Channel:** {channel.mention} (`#{channel.name}`)\n"
        f"**Type:** `{str(channel.type).title()}`"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Channel ID: `{channel.id}`"),
        accent_color=discord.Color.from_rgb(87, 242, 135),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_channel_delete_log_view(
    channel: discord.abc.GuildChannel,
) -> tuple[LayoutView, discord.File]:
    """Generates visual log for channel deletion (single red Discord channel pill)."""
    type_key = _get_channel_type_key(channel)
    png_bytes = await render_channel_pill(
        channel_name=channel.name,
        channel_type=type_key,
        is_deleted=True,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="channel_delete.png")

    item = discord.MediaGalleryItem("attachment://channel_delete.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_HASHTAG} Channel Deleted\n"
        f"**Name:** `#{channel.name}`\n"
        f"**Type:** `{str(channel.type).title()}`"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Channel ID: `{channel.id}`"),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_channel_update_log_view(
    channel: discord.abc.GuildChannel,
    before_name: str,
    after_name: str,
) -> tuple[LayoutView, discord.File]:
    """Generates a Discord Components V2 log container for channel rename with visual Discord channel pills."""
    type_key = _get_channel_type_key(channel)
    png_bytes = await render_channel_update(
        before_name=before_name,
        after_name=after_name,
        channel_type=type_key,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="channel_update.png")

    item = discord.MediaGalleryItem("attachment://channel_update.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_HASHTAG} Channel Updated\n"
        f"**Channel:** {channel.mention} (`{channel.id}`)"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Channel ID: `{channel.id}`"),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_role_create_log_view(
    role: discord.Role,
) -> tuple[LayoutView, discord.File]:
    """Generates visual log for role creation (single Discord role pill)."""
    color_hex = str(role.color) if role.color.value != 0 else "#99aab5"
    png_bytes = await render_role_pill(
        role_name=role.name,
        role_color_hex=color_hex,
        is_deleted=False,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="role_create.png")

    item = discord.MediaGalleryItem("attachment://role_create.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_DOTSTAR} Role Created\n"
        f"**Role:** {role.mention} (`{role.name}`)"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Role ID: `{role.id}`"),
        accent_color=discord.Color.from_rgb(87, 242, 135),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_role_delete_log_view(
    role: discord.Role,
) -> tuple[LayoutView, discord.File]:
    """Generates visual log for role deletion (single deleted role pill)."""
    color_hex = str(role.color) if role.color.value != 0 else "#99aab5"
    png_bytes = await render_role_pill(
        role_name=role.name,
        role_color_hex=color_hex,
        is_deleted=True,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="role_delete.png")

    item = discord.MediaGalleryItem("attachment://role_delete.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_DOTSTAR} Role Deleted\n"
        f"**Role Name:** `{role.name}`"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Role ID: `{role.id}`"),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_role_update_log_view(
    role: discord.Role,
    before_name: str,
    after_name: str,
    before_color_hex: str,
    after_color_hex: str,
) -> tuple[LayoutView, discord.File]:
    """Generates a Discord Components V2 log container for role update with visual role pills."""
    png_bytes = await render_role_update(
        before_name=before_name,
        after_name=after_name,
        before_color_hex=before_color_hex,
        after_color_hex=after_color_hex,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="role_update.png")

    item = discord.MediaGalleryItem("attachment://role_update.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_DOTSTAR} Role Updated\n"
        f"**Role:** {role.mention} (`{role.id}`)"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Role ID: `{role.id}`"),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_role_permissions_update_log_view(
    role: discord.Role,
    changed_perms: list[dict],
) -> tuple[LayoutView, discord.File]:
    """Generates visual log for role permission changes using Discord toggle switches."""
    color_hex = str(role.color) if role.color.value != 0 else "#99aab5"
    png_bytes = await render_role_permissions_update(
        role_name=role.name,
        role_color_hex=color_hex,
        changed_perms=changed_perms,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="role_perm.png")

    item = discord.MediaGalleryItem("attachment://role_perm.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_DOTSTAR} Role Permissions Updated\n"
        f"**Role:** {role.mention} (`{role.id}`)"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Role ID: `{role.id}`"),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


async def create_guild_update_log_view(
    guild: discord.Guild,
    before_name: str,
    after_name: str,
) -> tuple[LayoutView, discord.File]:
    """Generates a Discord Components V2 log container for server name update."""
    icon_url = guild.icon.url if guild.icon else None
    png_bytes = await render_server_update(
        before_name=before_name,
        after_name=after_name,
        icon_url=icon_url,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="guild_update.png")

    item = discord.MediaGalleryItem("attachment://guild_update.png")
    gallery = MediaGallery(item)

    header_text = (
        f"### {config.EMOJI_GEAR} Server Name Updated\n"
        f"**Server:** **{guild.name}** (`{guild.id}`)"
    )

    container = Container(
        TextDisplay(header_text),
        Separator(),
        gallery,
        TextDisplay(f"-# Server ID: `{guild.id}`"),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )

    view = LayoutView()
    view.add_item(container)
    return view, file


# ==========================================
# STANDARD AUDIT EMBEDS (MEMBERS & GUILD)
# ==========================================

def member_join_log_embed(member: discord.Member) -> discord.Embed:
    embed = _base_log_embed(
        f"{config.EMOJI_MEMBER_JOIN} Member Joined",
        LOG_COLOR_GREEN,
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    created_ts = int(member.created_at.timestamp())
    total_members = member.guild.member_count or len(member.guild.members)

    embed.add_field(
        name=f"{config.EMOJI_DOTSTAR} User",
        value=f"{member.mention} (`{member.name}` | `{member.id}`)",
        inline=False,
    )
    embed.add_field(
        name="Account Created",
        value=f"<t:{created_ts}:F>\n(<t:{created_ts}:R>)",
        inline=True,
    )
    embed.add_field(name="Member Count", value=f"`{total_members}`", inline=True)
    return embed


def member_leave_log_embed(member: discord.Member) -> discord.Embed:
    embed = _base_log_embed(
        f"{config.EMOJI_MEMBER_LEFT} Member Left",
        LOG_COLOR_RED,
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    joined_ts = int(member.joined_at.timestamp()) if member.joined_at else None
    joined_str = f"<t:{joined_ts}:F>\n(<t:{joined_ts}:R>)" if joined_ts else "Unknown"
    total_members = member.guild.member_count or len(member.guild.members)

    embed.add_field(
        name=f"{config.EMOJI_DOTSTAR} User",
        value=f"{member.mention} (`{member.name}` | `{member.id}`)",
        inline=False,
    )
    embed.add_field(name="Joined Server", value=joined_str, inline=True)
    embed.add_field(name="Member Count", value=f"`{total_members}`", inline=True)

    roles = [role.mention for role in reversed(member.roles) if role != member.guild.default_role]
    if roles:
        embed.add_field(name="Roles Held", value=" ".join(roles[:10]), inline=False)

    return embed


def member_roles_update_log_embed(
    member: discord.Member,
    added_roles: list[discord.Role],
    removed_roles: list[discord.Role],
) -> discord.Embed:
    embed = _base_log_embed(
        f"{config.EMOJI_DOTSTAR} Member Roles Updated",
        LOG_COLOR_BLUE,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name=f"{config.EMOJI_DOTSTAR} User",
        value=f"{member.mention} (`{member.id}`)",
        inline=False,
    )

    if added_roles:
        embed.add_field(
            name="➕ Added Roles",
            value=" ".join(r.mention for r in added_roles),
            inline=False,
        )
    if removed_roles:
        embed.add_field(
            name="➖ Removed Roles",
            value=" ".join(r.mention for r in removed_roles),
            inline=False,
        )

    return embed


def guild_update_log_embed(guild: discord.Guild, changes: list[str]) -> discord.Embed:
    embed = _base_log_embed(
        f"{config.EMOJI_GEAR} Server Settings Updated",
        LOG_COLOR_YELLOW,
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Server", value=f"**{guild.name}** (`{guild.id}`)", inline=False)
    embed.add_field(
        name="Changes",
        value="\n".join(f"{config.EMOJI_ARROW_RIGHT} {c}" for c in changes),
        inline=False,
    )
    return embed
