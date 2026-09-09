# -*- coding: utf-8 -*-
"""
cogs/achievements.py
Achievement tracking and display system.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from functions.achievements import (
    get_all_achievements,
    get_user_achievements,
    get_achievement_progress,
    check_and_unlock_achievements,
    award_achievement_rewards
)

logger = logging.getLogger("miso.cogs.achievements")


class Achievements(commands.Cog):
    """Achievement system."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="achievements", description="View your or someone else's achievements")
    @app_commands.describe(user="The user to check (defaults to yourself)")
    async def achievements_command(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None
    ) -> None:
        """View achievements."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        target = user or interaction.user
        
        all_achievements = await get_all_achievements()
        user_achievements = await get_user_achievements(interaction.guild.id, target.id)
        progress = await get_achievement_progress(interaction.guild.id, target.id)
        
        unlocked_ids = [a['achievement_id'] for a in user_achievements]
        
        # Group by category
        categories = {}
        for ach in all_achievements:
            cat = ach.get('category', 'other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ach)
        
        from functions.embed_customizations import build_custom_embed

        default_embed = discord.Embed(
            title=f"🏆 {target.display_name}'s Achievements",
            description=f"**{progress['unlocked_count']}/{progress['total_count']}** unlocked ({progress['completion_percentage']}%)",
            color=discord.Color.gold()
        )

        embed = await build_custom_embed(
            interaction.guild.id,
            'achievements_list',
            default_embed,
            user_name=target.display_name,
            unlocked=progress['unlocked_count'],
            total=progress['total_count'],
            percent=progress['completion_percentage'],
        )
        
        # Always add the dynamic achievement category fields
        category_names = {
            'social': '💬 Social',
            'levels': '⭐ Levels',
            'economy': '💰 Economy',
            'voice': '🎤 Voice',
            'special': '✨ Special'
        }
        
        # Clear any template fields from custom embed and re-add real ones
        embed.clear_fields()

        for cat, achievements in categories.items():
            cat_name = category_names.get(cat, cat.title())
            
            ach_text = ""
            for ach in achievements[:5]:
                icon = ach.get('icon', '🏅')
                name = ach['name']
                
                if ach['id'] in unlocked_ids:
                    ach_text += f"{icon} ~~{name}~~ ✅\n"
                elif ach.get('is_hidden'):
                    ach_text += f"🔒 ???\n"
                else:
                    ach_text += f"{icon} {name}\n"
            
            if ach_text:
                embed.add_field(name=cat_name, value=ach_text, inline=True)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        if not embed.footer.text:
            embed.set_footer(text="💡 Unlock achievements by playing! Use /achievement [name] for details")
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="achievement", description="View details about a specific achievement")
    @app_commands.describe(name="The achievement name")
    async def achievement_detail_command(
        self,
        interaction: discord.Interaction,
        name: str
    ) -> None:
        """View achievement details."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        all_achievements = await get_all_achievements()
        user_achievements = await get_user_achievements(interaction.guild.id, interaction.user.id)
        unlocked_ids = [a['achievement_id'] for a in user_achievements]
        
        # Find achievement by name (case insensitive)
        achievement = None
        for ach in all_achievements:
            if ach['name'].lower() == name.lower():
                achievement = ach
                break
        
        if not achievement:
            await interaction.followup.send(f"❌ Achievement '{name}' not found.", ephemeral=True)
            return
        
        is_unlocked = achievement['id'] in unlocked_ids
        icon = achievement.get('icon', '🏅')
        
        embed = discord.Embed(
            title=f"{icon} {achievement['name']}",
            description=achievement['description'],
            color=discord.Color.gold() if is_unlocked else discord.Color.greyple()
        )
        
        # Rewards
        rewards = []
        if achievement.get('reward_xp', 0) > 0:
            rewards.append(f"⭐ {achievement['reward_xp']} XP")
        if achievement.get('reward_coins', 0) > 0:
            rewards.append(f"🪙 {achievement['reward_coins']} coins")
        
        if rewards:
            embed.add_field(
                name="🎁 Rewards",
                value=" • ".join(rewards),
                inline=False
            )
        
        # Status
        if is_unlocked:
            embed.add_field(
                name="✅ Status",
                value="Unlocked!",
                inline=True
            )
        else:
            embed.add_field(
                name="🔒 Status",
                value="Locked",
                inline=True
            )
        
        # Category
        embed.add_field(
            name="📁 Category",
            value=achievement.get('category', 'other').title(),
            inline=True
        )
        
        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Check for achievement unlocks on messages."""
        if message.author.bot or not message.guild:
            return
        
        # Check achievements (don't await to avoid slowing down messages)
        try:
            newly_unlocked = await check_and_unlock_achievements(message.guild.id, message.author.id)
            
            # Announce new achievements
            for achievement in newly_unlocked:
                await self.announce_achievement(message.channel, message.author, achievement)
                await award_achievement_rewards(message.guild.id, message.author.id, achievement)
        except Exception as e:
            logger.error(f"Failed to check achievements: {e}")

    async def announce_achievement(self, channel: discord.TextChannel, user: discord.Member, achievement: dict):
        """Announce achievement unlock."""
        try:
            icon = achievement.get('icon', '🏅')
            
            default_embed = discord.Embed(
                title="🎉 Achievement Unlocked!",
                description=f"{user.mention} unlocked **{icon} {achievement['name']}**!",
                color=discord.Color.gold()
            )

            from functions.embed_customizations import build_custom_embed
            embed = await build_custom_embed(
                channel.guild.id,
                'achievement_unlock',
                default_embed,
                user=user.mention,
                user_name=user.display_name,
                achievement_name=f"{icon} {achievement['name']}",
                achievement_description=achievement['description'],
                reward_xp=achievement.get('reward_xp', 0),
                reward_coins=achievement.get('reward_coins', 0),
            )
            
            # Always add dynamic reward fields if not already in custom embed
            if not embed.fields:
                embed.add_field(name="Description", value=achievement['description'], inline=False)
                rewards = []
                if achievement.get('reward_xp', 0) > 0:
                    rewards.append(f"+{achievement['reward_xp']} XP")
                if achievement.get('reward_coins', 0) > 0:
                    rewards.append(f"+{achievement['reward_coins']} coins")
                if rewards:
                    embed.add_field(name="🎁 Rewards", value=" • ".join(rewards), inline=False)
            
            embed.set_thumbnail(url=user.display_avatar.url)
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to announce achievement: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Achievements(bot))
