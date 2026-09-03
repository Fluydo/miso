"""
Supabase synchronization utilities for caching Discord member data with clan tags.
This allows the dashboard to display clan tags which aren't available via Discord REST API.
"""

import os
from typing import Optional
from supabase import create_client, Client
import discord


# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cunbjamcjggtoayryluq.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Service role key, not anon key

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client with service role key."""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_SERVICE_KEY environment variable not set")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase_client


async def sync_member_to_db(member: discord.Member) -> None:
    """
    Sync a single member's data to Supabase guild_members table.
    Includes clan tag if available from primary_guild.
    """
    try:
        supabase = get_supabase()
        
        # Extract clan info
        clan_tag = None
        clan_badge_url = None
        primary_guild = getattr(member, "primary_guild", None)
        if primary_guild:
            clan_tag = getattr(primary_guild, "tag", None)
            badge = getattr(primary_guild, "badge", None)
            if badge:
                clan_badge_url = getattr(badge, "url", str(badge))
        
        # Get highest role color
        role_color = None
        role_icon = None
        if member.roles:
            sorted_roles = sorted(
                [r for r in member.roles if r.id != member.guild.default_role.id],
                key=lambda r: r.position,
                reverse=True
            )
            for role in sorted_roles:
                if role_color is None and role.color.value != 0:
                    role_color = role.color.value
                if role_icon is None and role.icon:
                    role_icon = role.icon.url
                if role_color and role_icon:
                    break
        
        # Build avatar URL
        avatar = None
        if member.avatar:
            avatar = member.avatar.url
        elif member.display_avatar:
            avatar = member.display_avatar.url
        
        # Build avatar decoration URL
        avatar_decoration = None
        if hasattr(member, "avatar_decoration") and member.avatar_decoration:
            avatar_decoration = member.avatar_decoration.url
        
        # Prepare member data
        member_data = {
            "guild_id": str(member.guild.id),
            "user_id": str(member.id),
            "username": member.name,
            "discriminator": member.discriminator if member.discriminator != "0" else "0",
            "avatar": avatar,
            "avatar_decoration": avatar_decoration,
            "nickname": member.nick,
            "clan_tag": clan_tag,
            "clan_badge_url": clan_badge_url,
            "role_color": role_color,
            "role_icon": role_icon,
        }
        
        # Upsert to database (insert or update)
        supabase.table("guild_members").upsert(
            member_data,
            on_conflict="guild_id,user_id"
        ).execute()
        
    except Exception as e:
        print(f"Error syncing member {member.id} to Supabase: {e}")


async def sync_guild_members(guild: discord.Guild) -> int:
    """
    Sync all members of a guild to Supabase.
    Returns the number of members synced.
    """
    count = 0
    for member in guild.members:
        await sync_member_to_db(member)
        count += 1
    return count


async def remove_member_from_db(guild_id: int, user_id: int) -> None:
    """Remove a member from the database when they leave."""
    try:
        supabase = get_supabase()
        supabase.table("guild_members").delete().match({
            "guild_id": str(guild_id),
            "user_id": str(user_id)
        }).execute()
    except Exception as e:
        print(f"Error removing member {user_id} from Supabase: {e}")
