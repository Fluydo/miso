"""
cogs/invites.py
Invite tracking system for Miso Bot.

Responsibilities:
- Build and maintain an in-memory invite cache per guild (code -> uses count).
- On member join: diff cache against live Discord invites to determine which code was used.
- Persist every join/leave to invites.json so stats survive bot restarts.
- Expose /invites and /invites leaderboard slash commands.
"""

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from functions.invites import (
    bulk_sync_invites,
    delete_invite,
    get_invite_stats,
    get_leaderboard,
    record_join,
    record_leave,
    upsert_invite,
)
from functions.moderation import send_mod_log
from embeds.invites import (
    invite_join_log_embed,
    invites_embed,
    invites_leaderboard_embed,
)
from embeds.errors import error_embed

logger = logging.getLogger("miso.cogs.invites")


class Invites(commands.Cog):
    """Invite tracking, statistics, and leaderboard commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # { guild_id: { invite_code: uses_count } }
        self._cache: dict[int, dict[str, int]] = {}
        # Per-guild locks to prevent race conditions when multiple members join at once
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self._locks:
            self._locks[guild_id] = asyncio.Lock()
        return self._locks[guild_id]

    # ==========================================
    # CACHE HELPERS
    # ==========================================

    async def _fetch_invites(self, guild: discord.Guild) -> dict[str, int]:
        """
        Fetches all current invites from Discord and returns {code: uses}.
        Requires the bot to have Manage Guild permission.
        """
        try:
            invites = await guild.invites()
            return {inv.code: inv.uses or 0 for inv in invites}
        except discord.Forbidden:
            logger.warning(f"Missing 'Manage Guild' permission in {guild.name} — cannot fetch invites.")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch invites for {guild.name}: {e}")
            return {}

    async def _rebuild_cache(self, guild: discord.Guild) -> None:
        """
        (Re)builds the in-memory cache and syncs the JSON store for one guild.
        Called on on_ready and after reconnects.
        """
        live = await self._fetch_invites(guild)
        self._cache[guild.id] = live

        # Build snapshot dict for JSON persistence
        snapshot: dict[str, dict] = {}
        try:
            discord_invites = await guild.invites()
            for inv in discord_invites:
                snapshot[inv.code] = {
                    "inviter_id": inv.inviter.id if inv.inviter else None,
                    "uses": inv.uses or 0,
                    "max_uses": inv.max_uses or 0,
                    "max_age": inv.max_age or 0,
                }
        except Exception:
            pass

        if snapshot:
            bulk_sync_invites(guild.id, snapshot)
        logger.debug(f"Invite cache rebuilt for {guild.name} ({len(live)} invites).")

    # ==========================================
    # BOT EVENTS
    # ==========================================

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Rebuild invite cache for all guilds on bot startup."""
        for guild in self.bot.guilds:
            await self._rebuild_cache(guild)
        logger.info(f"Invite cache built for {len(self.bot.guilds)} guild(s).")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Build cache when the bot joins a new guild."""
        await self._rebuild_cache(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Clean up cache when the bot leaves a guild."""
        self._cache.pop(guild.id, None)
        self._locks.pop(guild.id, None)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        """Add new invites to cache and JSON."""
        if not invite.guild:
            return
        guild_id = invite.guild.id
        code = invite.code

        # Update in-memory cache
        if guild_id not in self._cache:
            self._cache[guild_id] = {}
        self._cache[guild_id][code] = invite.uses or 0

        # Persist to JSON
        upsert_invite(
            guild_id=guild_id,
            code=code,
            inviter_id=invite.inviter.id if invite.inviter else None,
            uses=invite.uses or 0,
            max_uses=invite.max_uses or 0,
            max_age=invite.max_age or 0,
        )

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        """Remove deleted/expired invites from cache and JSON."""
        if not invite.guild:
            return
        guild_id = invite.guild.id
        code = invite.code

        if guild_id in self._cache:
            self._cache[guild_id].pop(code, None)
        delete_invite(guild_id, code)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """
        Determine which invite was used, record the join, and post a log.
        Uses a per-guild lock to prevent race conditions.
        """
        guild = member.guild

        async with self._lock(guild.id):
            # Snapshot the cache BEFORE fetching fresh data
            old_cache = dict(self._cache.get(guild.id, {}))

            # Fetch the current live invite list from Discord
            new_cache = await self._fetch_invites(guild)
            self._cache[guild.id] = new_cache

            used_code: Optional[str] = None
            inviter_id: Optional[int] = None

            # Diff: find the invite whose uses count increased by 1
            for code, new_uses in new_cache.items():
                old_uses = old_cache.get(code, 0)
                if new_uses > old_uses:
                    used_code = code
                    break

            # If we found the code, resolve the inviter from JSON store
            if used_code:
                from functions.invites import get_guild_invites
                stored_invites = get_guild_invites(guild.id)
                inv_record = stored_invites.get(used_code, {})
                inviter_id = inv_record.get("inviter_id")

                # Also try fetching from Discord directly for freshness
                if inviter_id is None:
                    try:
                        discord_invites = await guild.invites()
                        for inv in discord_invites:
                            if inv.code == used_code and inv.inviter:
                                inviter_id = inv.inviter.id
                                # Update JSON with the inviter now that we know it
                                upsert_invite(
                                    guild_id=guild.id,
                                    code=used_code,
                                    inviter_id=inviter_id,
                                    uses=inv.uses or 0,
                                    max_uses=inv.max_uses or 0,
                                    max_age=inv.max_age or 0,
                                )
                                break
                    except Exception:
                        pass

            # Check vanity URL as a fallback if no code found
            if used_code is None:
                try:
                    vanity = await guild.vanity_invite()
                    if vanity:
                        vanity_old = old_cache.get(f"vanity:{vanity.code}", 0)
                        vanity_new = vanity.uses or 0
                        if vanity_new > vanity_old:
                            used_code = vanity.code
                            # Attribute vanity joins to None (shown as "Vanity URL")
                            inviter_id = None
                            self._cache[guild.id][f"vanity:{vanity.code}"] = vanity_new
                except (discord.HTTPException, discord.Forbidden):
                    pass

        # Persist the join record
        record_join(
            guild_id=guild.id,
            member_id=member.id,
            inviter_id=inviter_id,
            code=used_code,
        )

        # Get fresh stats for inviter to show in log
        total_invites = 0
        if inviter_id:
            stats = get_invite_stats(guild.id, inviter_id)
            total_invites = stats.get("total", 0)

        # Post invite join log to the audit log channel
        log_embed = invite_join_log_embed(
            member=member,
            inviter_id=inviter_id,
            invite_code=used_code,
            total_invites=total_invites,
        )
        await send_mod_log(guild, log_embed, log_type="members")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Mark the member's join record as 'left'."""
        record_leave(guild_id=member.guild.id, member_id=member.id)

    # ==========================================
    # SLASH COMMANDS
    # ==========================================

    invites_group = app_commands.Group(
        name="invites",
        description="View invite statistics for yourself, another user, or the server leaderboard.",
        guild_only=True,
    )

    @invites_group.command(name="stats", description="View invite statistics for yourself or another user.")
    @app_commands.describe(user="The user to check invites for (leave empty for yourself)")
    async def invites_stats(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
    ) -> None:
        if not interaction.guild:
            return

        target = user or interaction.user
        stats = get_invite_stats(interaction.guild.id, target.id)
        embed = invites_embed(target, stats, interaction.guild)
        await interaction.response.send_message(embed=embed)

    @invites_group.command(name="leaderboard", description="Show the top inviters in this server.")
    async def invites_leaderboard(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        entries = get_leaderboard(interaction.guild.id, limit=50)
        if not entries:
            await interaction.response.send_message(
                "*No invites recorded for this server yet.*",
                ephemeral=True,
            )
            return

        def formatter(item):
            return f"{item.get('active', 0)} Active ({item.get('total', 0)} total)"

        from cogs.games import LeaderboardPaginationView

        # LeaderboardPaginationView expects "user_id" — remap from "inviter_id"
        normalized = [
            {**e, "user_id": e["inviter_id"]}
            for e in entries
        ]

        view = LeaderboardPaginationView(
            bot=self.bot,
            all_data=normalized,
            title="🔗 Invites Leaderboard",
            value_formatter=formatter,
            user_id=interaction.user.id,
            per_page=5,
        )

        await interaction.response.defer()
        file = await view.get_rendered_page_file()
        await interaction.followup.send(file=file, view=view)

    @invites_group.command(name="reset", description="Reset all invite data for a user. Admin only.")
    @app_commands.describe(user="The user whose invite records will be cleared")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def invites_reset(
        self,
        interaction: discord.Interaction,
        user: discord.User,
    ) -> None:
        """Clears all join records attributed to a specific inviter."""
        if not interaction.guild:
            return

        from functions.invites import load_invites, save_invites, _guild_data
        data = load_invites()
        guild = _guild_data(data, interaction.guild.id)
        members = guild.get("members", {})

        cleared = 0
        for record in members.values():
            if record.get("inviter_id") == user.id:
                record["inviter_id"] = None
                record["invite_code"] = None
                cleared += 1

        save_invites(data)

        embed = discord.Embed(
            description=(
                f"{config.EMOJI_TICK} Reset invite attribution for **<@{user.id}>**.\n"
                f"Cleared `{cleared}` member record(s)."
            ),
            color=config.COLOR_SUCCESS,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Invites(bot))
