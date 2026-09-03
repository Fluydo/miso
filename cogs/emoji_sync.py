"""
cogs/emoji_sync.py
Automatically sync Discord emojis to Supabase on bot ready.
"""

import discord
from discord.ext import commands
import logging

from functions.emoji_supabase import sync_guild_emojis

logger = logging.getLogger("miso.emoji_sync")


class EmojiSync(commands.Cog):
    """Sync Discord emojis to Supabase for web dashboard."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.synced_guilds = set()

    @commands.Cog.listener()
    async def on_ready(self):
        """Sync all guild emojis when bot is ready."""
        logger.info("Starting emoji sync to Supabase...")
        
        for guild in self.bot.guilds:
            if guild.id not in self.synced_guilds:
                success = await sync_guild_emojis(guild)
                if success:
                    self.synced_guilds.add(guild.id)
                    logger.info(f"✓ Synced emojis for {guild.name}")
                else:
                    logger.warning(f"✗ Failed to sync emojis for {guild.name}")

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: list, after: list):
        """Re-sync emojis when they're updated."""
        logger.info(f"Emoji update detected in {guild.name}, re-syncing...")
        await sync_guild_emojis(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Sync emojis when bot joins a new guild."""
        logger.info(f"Joined new guild {guild.name}, syncing emojis...")
        await sync_guild_emojis(guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(EmojiSync(bot))
