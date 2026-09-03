"""
Cog for syncing Discord member data to Supabase for dashboard access.
Keeps clan tags and other member info up-to-date in the database.
"""

import discord
from discord.ext import commands, tasks
from functions.supabase_sync import sync_member_to_db, sync_guild_members, remove_member_from_db


class SupabaseSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sync_all_guilds.start()
    
    def cog_unload(self):
        self.sync_all_guilds.cancel()
    
    @tasks.loop(hours=1)
    async def sync_all_guilds(self):
        """Sync all guild members every hour to keep data fresh."""
        print("[SupabaseSync] Starting periodic guild member sync...")
        total = 0
        for guild in self.bot.guilds:
            try:
                count = await sync_guild_members(guild)
                total += count
                print(f"[SupabaseSync] Synced {count} members from {guild.name}")
            except Exception as e:
                print(f"[SupabaseSync] Error syncing guild {guild.id}: {e}")
        print(f"[SupabaseSync] Completed sync of {total} members across {len(self.bot.guilds)} guilds")
    
    @sync_all_guilds.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Sync new member to database."""
        await sync_member_to_db(member)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove member from database when they leave."""
        await remove_member_from_db(member.guild.id, member.id)
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Update member data when it changes (nickname, roles, clan tag, etc)."""
        # Check if anything relevant changed
        if (before.nick != after.nick or 
            before.roles != after.roles or
            before.avatar != after.avatar or
            getattr(before, "primary_guild", None) != getattr(after, "primary_guild", None)):
            await sync_member_to_db(after)
    
    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Update user data when username/avatar changes."""
        if before.name != after.name or before.avatar != after.avatar:
            # Update in all guilds where this user is a member
            for guild in self.bot.guilds:
                member = guild.get_member(after.id)
                if member:
                    await sync_member_to_db(member)
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Sync all members when bot joins a new guild."""
        print(f"[SupabaseSync] Bot joined {guild.name}, syncing members...")
        count = await sync_guild_members(guild)
        print(f"[SupabaseSync] Synced {count} members from {guild.name}")
    
    @commands.command(name="syncmembers", hidden=True)
    @commands.is_owner()
    async def sync_members_command(self, ctx: commands.Context, guild_id: int = None):
        """Manually trigger member sync for a guild or all guilds."""
        if guild_id:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return await ctx.send(f"❌ Guild {guild_id} not found")
            count = await sync_guild_members(guild)
            await ctx.send(f"✅ Synced {count} members from {guild.name}")
        else:
            total = 0
            for guild in self.bot.guilds:
                count = await sync_guild_members(guild)
                total += count
            await ctx.send(f"✅ Synced {total} members across {len(self.bot.guilds)} guilds")


async def setup(bot: commands.Bot):
    await bot.add_cog(SupabaseSync(bot))
