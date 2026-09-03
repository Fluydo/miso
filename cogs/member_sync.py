"""
Member sync cog - Syncs guild member data (avatars, clan tags, roles) to Supabase
"""

import logging
from typing import Optional
import discord
from discord.ext import commands, tasks
from supabase import create_client, Client
import config

logger = logging.getLogger("miso.member_sync")


class MemberSync(commands.Cog):
    """Sync guild member data to Supabase for dashboard."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase: Optional[Client] = None
        
        # Initialize Supabase client
        if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
            self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            logger.info("Member sync initialized with Supabase")
        else:
            logger.warning("Supabase not configured, member sync disabled")

    async def cog_load(self):
        """Start background sync task when cog loads."""
        if self.supabase:
            self.bulk_sync_members.start()
            logger.info("Started bulk member sync task")

    async def cog_unload(self):
        """Stop background sync task when cog unloads."""
        self.bulk_sync_members.cancel()

    def _format_member_data(self, member: discord.Member) -> dict:
        """Format member data for database storage."""
        # Get highest role with color
        role_color = None
        highest_position = -1
        for role in member.roles:
            if role.color.value and role.position > highest_position:
                role_color = role.color.value
                highest_position = role.position

        # Get highest role with icon
        role_icon = None
        role_id = None
        icon_position = -1
        for role in member.roles:
            if role.icon and role.position > icon_position:
                role_icon = str(role.icon.url) if role.icon else None
                role_id = str(role.id)
                icon_position = role.position

        # Build avatar URL
        avatar_url = None
        if member.avatar:
            avatar_url = str(member.avatar.url)
        elif member.display_avatar:
            avatar_url = str(member.display_avatar.url)

        # Avatar decoration
        avatar_decoration_url = None
        if hasattr(member, 'avatar_decoration') and member.avatar_decoration:
            avatar_decoration_url = str(member.avatar_decoration.url)

        # Clan tag from primary_guild (if available via Gateway)
        clan_tag = None
        clan_badge_url = None
        if hasattr(member, '_user'):
            user = member._user
            if hasattr(user, 'clan') and user.clan:
                clan_tag = user.clan.tag
                if user.clan.badge:
                    clan_badge_url = f"https://cdn.discordapp.com/clan-badges/{user.clan.identity_guild_id}/{user.clan.badge}.png"

        return {
            "guild_id": str(member.guild.id),
            "user_id": str(member.id),
            "username": member.name,
            "discriminator": member.discriminator if member.discriminator != "0" else "0",
            "avatar": avatar_url,
            "avatar_decoration": avatar_decoration_url,
            "nickname": member.nick,
            "clan_tag": clan_tag,
            "clan_badge_url": clan_badge_url,
            "role_color": role_color,
            "role_icon": role_icon,
        }

    async def sync_member(self, member: discord.Member):
        """Sync a single member to database."""
        if not self.supabase:
            return

        try:
            data = self._format_member_data(member)
            
            # Upsert to database
            self.supabase.table("guild_members").upsert(data).execute()
            
            if data.get("clan_tag"):
                logger.debug(f"Synced member {member.name} with clan tag {data['clan_tag']}")
            
        except Exception as e:
            logger.error(f"Failed to sync member {member.id}: {e}")

    @tasks.loop(minutes=30)
    async def bulk_sync_members(self):
        """Bulk sync all members from all guilds every 30 minutes."""
        if not self.supabase:
            return

        logger.info("Starting bulk member sync...")
        synced = 0
        with_tags = 0

        for guild in self.bot.guilds:
            try:
                # Fetch all members (may take time for large guilds)
                await guild.chunk()
                
                batch = []
                for member in guild.members:
                    if member.bot:
                        continue
                    
                    data = self._format_member_data(member)
                    batch.append(data)
                    
                    if data.get("clan_tag"):
                        with_tags += 1
                
                # Batch upsert
                if batch:
                    self.supabase.table("guild_members").upsert(batch).execute()
                    synced += len(batch)
                    logger.info(f"Synced {len(batch)} members from {guild.name}")
                
            except Exception as e:
                logger.error(f"Failed to sync guild {guild.id}: {e}")

        logger.info(f"Bulk sync complete: {synced} members synced, {with_tags} with clan tags")

    @bulk_sync_members.before_loop
    async def before_bulk_sync(self):
        """Wait until bot is ready before starting sync."""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Sync member when their profile changes."""
        # Only sync if relevant fields changed
        if (before.avatar != after.avatar or 
            before.nick != after.nick or
            before.roles != after.roles or
            getattr(getattr(before, '_user', None), 'clan', None) != getattr(getattr(after, '_user', None), 'clan', None)):
            await self.sync_member(after)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Sync new member when they join."""
        await self.sync_member(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove member from database when they leave."""
        if not self.supabase:
            return
        
        try:
            self.supabase.table("guild_members").delete().eq("guild_id", str(member.guild.id)).eq("user_id", str(member.id)).execute()
            logger.debug(f"Removed member {member.id} from database")
        except Exception as e:
            logger.error(f"Failed to remove member {member.id}: {e}")

    @commands.command(name="syncmembers")
    @commands.has_permissions(administrator=True)
    async def sync_members_command(self, ctx: commands.Context):
        """Manually trigger member sync for this server."""
        if not self.supabase:
            return await ctx.send("❌ Supabase not configured!")

        msg = await ctx.send("🔄 Syncing members...")
        
        try:
            await ctx.guild.chunk()
            
            batch = []
            with_tags = 0
            for member in ctx.guild.members:
                if member.bot:
                    continue
                
                data = self._format_member_data(member)
                batch.append(data)
                
                if data.get("clan_tag"):
                    with_tags += 1
            
            if batch:
                self.supabase.table("guild_members").upsert(batch).execute()
                await msg.edit(content=f"✅ Synced **{len(batch)}** members ({with_tags} with clan tags)")
            else:
                await msg.edit(content="⚠️ No members to sync")
                
        except Exception as e:
            logger.error(f"Sync command failed: {e}", exc_info=True)
            await msg.edit(content=f"❌ Sync failed: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberSync(bot))
