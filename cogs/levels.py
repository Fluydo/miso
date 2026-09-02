"""
cogs/levels.py
Leveling & XP Cog for Miso Bot.

Features:
- Chat XP accumulation with 60-second cooldown.
- Automatic creation and assignment of 5 milestone roles (Level 5, 10, 15, 20, 25).
- /rank [@user] — Displays a custom visual rank card.
- /levels — Paginated visual server level leaderboard.
- /level set/give/remove — Admin level management with visual cards.
- /level xp set/give/remove — Admin XP management with visual cards.
"""

import io
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from cogs.games import LeaderboardPaginationView
from functions.levels import (
    LEVEL_MILESTONES,
    MILESTONE_ROLE_COLORS,
    MILESTONE_ROLE_NAMES,
    add_xp,
    admin_give_level,
    admin_give_xp,
    admin_set_level,
    admin_set_xp,
    get_levels_leaderboard,
    get_user_level,
)
from functions.renderer import render_rank_card

logger = logging.getLogger("miso.cogs.levels")


async def _send_rank_card(
    interaction: discord.Interaction,
    target: discord.User | discord.Member,
    level: int,
    xp: int,
    next_req: int,
) -> None:
    """Helper to render and send a rank card as a followup."""
    _, __, ___, rank_pos = get_user_level(interaction.guild.id, target.id)
    png_bytes = await render_rank_card(
        avatar_url=target.display_avatar.url,
        username=target.name,
        level=level,
        current_xp=xp,
        required_xp=next_req,
        rank_pos=rank_pos,
    )
    file = discord.File(io.BytesIO(png_bytes), filename="rank.png")
    await interaction.followup.send(file=file)


class Levels(commands.Cog):
    """Chat XP progression and milestone tier roles."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _ensure_milestone_roles(self, guild: discord.Guild) -> dict[int, discord.Role]:
        """Finds or creates the 4 milestone tier roles on the server with gradients and icons if available."""
        from functions.levels import MILESTONE_ROLE_ICONS, MILESTONE_ROLE_GRADIENTS
        
        roles_by_lvl = {}
        
        # Check if guild has role icon feature (boost level 2+)
        has_role_icons = guild.premium_tier >= 2
        
        for lvl in LEVEL_MILESTONES:
            role_name = MILESTONE_ROLE_NAMES[lvl]
            existing_role = discord.utils.get(guild.roles, name=role_name)
            
            if not existing_role:
                try:
                    # Use gradient color if available, otherwise base color
                    if has_role_icons and lvl in MILESTONE_ROLE_GRADIENTS:
                        # Use the lighter shade for better visibility
                        color_value = MILESTONE_ROLE_GRADIENTS[lvl][1]
                    else:
                        color_value = MILESTONE_ROLE_COLORS[lvl]
                    
                    # Create role
                    existing_role = await guild.create_role(
                        name=role_name,
                        color=discord.Color(color_value),
                        reason=f"Auto-created level {lvl} milestone role",
                    )
                    
                    # Add role icon if guild supports it
                    if has_role_icons and lvl in MILESTONE_ROLE_ICONS:
                        try:
                            icon_emoji = self.bot.get_emoji(MILESTONE_ROLE_ICONS[lvl])
                            if icon_emoji:
                                await existing_role.edit(display_icon=icon_emoji)
                        except (discord.Forbidden, discord.HTTPException):
                            pass  # Icon setting failed, role still usable
                    
                except discord.Forbidden:
                    continue
            
            roles_by_lvl[lvl] = existing_role
        
        return roles_by_lvl

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        level, xp, leveled_up = add_xp(message.guild.id, message.author.id)
        if leveled_up:
            roles = await self._ensure_milestone_roles(message.guild)
            for m_lvl in LEVEL_MILESTONES:
                if level >= m_lvl and m_lvl in roles:
                    target_role = roles[m_lvl]
                    if target_role not in message.author.roles:
                        try:
                            await message.author.add_roles(target_role, reason=f"Reached Level {level} milestone")
                        except discord.Forbidden:
                            pass

    # ==========================================
    # /RANK
    # ==========================================
    @app_commands.command(name="rank", description="Check your or another user's level and rank card.")
    @app_commands.describe(user="The user to check level for (defaults to yourself)")
    async def rank(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
    ) -> None:
        if not interaction.guild:
            return

        target = user or interaction.user
        level, xp, next_req, rank_pos = get_user_level(interaction.guild.id, target.id)

        await interaction.response.defer()
        png_bytes = await render_rank_card(
            avatar_url=target.display_avatar.url,
            username=target.name,
            level=level,
            current_xp=xp,
            required_xp=next_req,
            rank_pos=rank_pos,
        )
        file = discord.File(io.BytesIO(png_bytes), filename="rank.png")
        await interaction.followup.send(file=file)

    # ==========================================
    # /LEVELS
    # ==========================================
    @app_commands.command(name="levels", description="View the visual server level leaderboard.")
    async def levels(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        lb_data = get_levels_leaderboard(interaction.guild.id, limit=50)
        if not lb_data:
            await interaction.response.defer()
            await interaction.followup.send(
                "*No chat activity recorded for leveling yet. Start chatting!*",
                ephemeral=True,
            )
            return

        def formatter(item):
            return f"Level {item.get('level', 0)} ({item.get('xp', 0):,} XP)"

        view = LeaderboardPaginationView(
            bot=self.bot,
            all_data=lb_data,
            title="🏆 Level Leaderboard",
            value_formatter=formatter,
            user_id=interaction.user.id,
            per_page=5,
        )

        await interaction.response.defer()
        file = await view.get_rendered_page_file()
        await interaction.followup.send(file=file, view=view)

    # ==========================================
    # /LEVEL ADMIN GROUP
    # ==========================================
    level_group = app_commands.Group(
        name="level",
        description="Admin tools to manage member levels and XP.",
        guild_only=True,
    )

    @level_group.command(name="set", description="Set a member's level to an exact value.")
    @app_commands.describe(user="Target member", level="New level to set")
    @app_commands.checks.has_permissions(administrator=True)
    async def level_set(
        self, interaction: discord.Interaction, user: discord.Member, level: app_commands.Range[int, 0, 500]
    ) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer()
        new_level, new_xp, next_req = admin_set_level(interaction.guild.id, user.id, level)
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Set {user.mention}'s level to **{new_level}**.", ephemeral=True
        )
        await _send_rank_card(interaction, user, new_level, new_xp, next_req)

    @level_group.command(name="give", description="Give a member a number of levels.")
    @app_commands.describe(user="Target member", amount="Levels to give (use negative to remove)")
    @app_commands.checks.has_permissions(administrator=True)
    async def level_give(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer()
        new_level, new_xp, next_req = admin_give_level(interaction.guild.id, user.id, amount)
        sign = "+" if amount >= 0 else ""
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Gave {user.mention} `{sign}{amount}` levels → now **Level {new_level}**.", ephemeral=True
        )
        await _send_rank_card(interaction, user, new_level, new_xp, next_req)

    @level_group.command(name="remove", description="Remove levels from a member.")
    @app_commands.describe(user="Target member", amount="Number of levels to remove")
    @app_commands.checks.has_permissions(administrator=True)
    async def level_remove(
        self, interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1, 500]
    ) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer()
        new_level, new_xp, next_req = admin_give_level(interaction.guild.id, user.id, -amount)
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Removed `{amount}` levels from {user.mention} → now **Level {new_level}**.", ephemeral=True
        )
        await _send_rank_card(interaction, user, new_level, new_xp, next_req)

    # ==========================================
    # /LEVEL XP SUBGROUP
    # ==========================================
    level_xp_group = app_commands.Group(
        name="xp",
        description="Admin tools to manage member XP directly.",
        parent=level_group,
        guild_only=True,
    )

    @level_xp_group.command(name="set", description="Set a member's XP to an exact value (recalculates level).")
    @app_commands.describe(user="Target member", xp="New XP value to set")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_set(
        self, interaction: discord.Interaction, user: discord.Member, xp: app_commands.Range[int, 0, 9999999]
    ) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer()
        new_level, new_xp, next_req = admin_set_xp(interaction.guild.id, user.id, xp)
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Set {user.mention}'s XP to `{new_xp:,}` → **Level {new_level}**.", ephemeral=True
        )
        await _send_rank_card(interaction, user, new_level, new_xp, next_req)

    @level_xp_group.command(name="give", description="Give a member XP points.")
    @app_commands.describe(user="Target member", amount="XP to give (use negative to remove)")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_give(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer()
        new_level, new_xp, next_req = admin_give_xp(interaction.guild.id, user.id, amount)
        sign = "+" if amount >= 0 else ""
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Gave {user.mention} `{sign}{amount:,}` XP → now `{new_xp:,}` XP at **Level {new_level}**.", ephemeral=True
        )
        await _send_rank_card(interaction, user, new_level, new_xp, next_req)

    @level_xp_group.command(name="remove", description="Remove XP from a member.")
    @app_commands.describe(user="Target member", amount="XP to remove")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_remove(
        self, interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1, 9999999]
    ) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer()
        new_level, new_xp, next_req = admin_give_xp(interaction.guild.id, user.id, -amount)
        await interaction.followup.send(
            f"{config.EMOJI_TICK} Removed `{amount:,}` XP from {user.mention} → now `{new_xp:,}` XP at **Level {new_level}**.", ephemeral=True
        )
        await _send_rank_card(interaction, user, new_level, new_xp, next_req)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Levels(bot))
