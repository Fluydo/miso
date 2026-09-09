# -*- coding: utf-8 -*-
"""
cogs/voice_xp.py
Voice XP tracking - earn XP for being in voice channels.
"""

import logging
import discord
from discord.ext import commands

from functions.voice_xp import (
    start_voice_session,
    end_voice_session,
    update_voice_session_status,
    get_voice_xp_settings,
    get_user_voice_stats,
)
from functions.levels import admin_give_xp, get_user_level

logger = logging.getLogger("miso.cogs.voice_xp")


class VoiceXP(commands.Cog):
    """Voice XP tracking system."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _count_non_bot_members(self, voice_state: discord.VoiceState) -> int:
        """Count non-bot members in a voice channel."""
        if not voice_state.channel:
            return 0
        return len([m for m in voice_state.channel.members if not m.bot])

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Track voice channel joins, leaves, and status changes."""
        
        if member.bot:
            return
        
        guild_id = member.guild.id
        user_id = member.id
        
        # Get settings
        settings = await get_voice_xp_settings(guild_id)
        if not settings['enabled']:
            return
        
        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            # Check if enough members
            member_count = self._count_non_bot_members(after)
            if member_count >= settings['min_members_required']:
                is_streaming = after.self_stream or False
                is_video = after.self_video or False
                await start_voice_session(guild_id, user_id, after.channel.id, is_streaming, is_video)
                logger.debug(f"User {member.name} joined voice in guild {member.guild.name}")
        
        # User left a voice channel
        elif before.channel is not None and after.channel is None:
            xp_earned = await end_voice_session(guild_id, user_id)
            if xp_earned and xp_earned > 0:
                # Award XP to levels system with boost multiplier
                from functions.levels import add_xp_raw
                from functions.xp_boosts import get_boost_multiplier
                try:
                    boost_mult = await get_boost_multiplier(guild_id)
                    final_xp = int(xp_earned * boost_mult)
                    add_xp_raw(guild_id, user_id, final_xp)
                    logger.info(f"User {member.name} earned {final_xp} voice XP (base: {xp_earned}, boost: {boost_mult}x)")
                except Exception as e:
                    logger.error(f"Failed to award voice XP: {e}")
        
        # User switched channels
        elif before.channel != after.channel:
            # End old session and start new one
            xp_earned = await end_voice_session(guild_id, user_id)
            if xp_earned and xp_earned > 0:
                from functions.levels import add_xp_raw
                from functions.xp_boosts import get_boost_multiplier
                try:
                    boost_mult = await get_boost_multiplier(guild_id)
                    final_xp = int(xp_earned * boost_mult)
                    add_xp_raw(guild_id, user_id, final_xp)
                except:
                    pass
            
            # Start new session
            member_count = self._count_non_bot_members(after)
            if member_count >= settings['min_members_required']:
                is_streaming = after.self_stream or False
                is_video = after.self_video or False
                await start_voice_session(guild_id, user_id, after.channel.id, is_streaming, is_video)
        
        # User changed streaming/video status (in same channel)
        elif before.channel == after.channel:
            if (before.self_stream != after.self_stream) or (before.self_video != after.self_video):
                is_streaming = after.self_stream or False
                is_video = after.self_video or False
                await update_voice_session_status(guild_id, user_id, is_streaming, is_video)
                logger.debug(f"User {member.name} updated voice status: stream={is_streaming}, video={is_video}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceXP(bot))
