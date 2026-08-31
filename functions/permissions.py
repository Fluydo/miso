import discord


def is_moderator(member: discord.Member | discord.User) -> bool:
    """
    Checks if a member has moderator or staff level permissions.
    """
    if not isinstance(member, discord.Member):
        return False
    if member.id == member.guild.owner_id:
        return True
    return (
        member.guild_permissions.manage_messages
        or member.guild_permissions.manage_guild
        or member.guild_permissions.administrator
    )


def can_moderate(moderator: discord.Member, target: discord.Member) -> tuple[bool, str | None]:
    """
    Checks if a moderator has permission and role hierarchy to moderate a target member.
    Returns (True, None) if allowed, or (False, reason_string) if disallowed.
    """
    # 1. Prevent self-moderation
    if moderator.id == target.id:
        return False, "You cannot moderate yourself."

    # 2. Prevent moderating the bot
    if target.id == moderator.guild.me.id:
        return False, "I cannot moderate myself."

    # 3. Server owner immunity
    if target.id == moderator.guild.owner_id:
        return False, "You cannot moderate the server owner."

    # 4. Moderator hierarchy check (unless the moderator is the server owner)
    if moderator.id != moderator.guild.owner_id:
        if target.top_role >= moderator.top_role:
            return False, f"You cannot moderate {target.mention} because their highest role is equal to or higher than yours."

    # 5. Bot hierarchy check
    if target.top_role >= moderator.guild.me.top_role:
        return False, f"I cannot moderate {target.mention} because their highest role is equal to or higher than mine."

    return True, None


def bot_can_moderate(guild: discord.Guild, target: discord.Member) -> tuple[bool, str | None]:
    """
    Checks if the bot itself has the hierarchy and permissions to moderate the target member.
    """
    if target.id == guild.owner_id:
        return False, "I cannot moderate the server owner."

    if target.id == guild.me.id:
        return False, "I cannot moderate myself."

    if target.top_role >= guild.me.top_role:
        return False, f"My highest role ({guild.me.top_role.mention}) is not high enough to moderate {target.mention}."

    return True, None
