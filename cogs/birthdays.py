"""
cogs/birthdays.py
Birthday tracking and automatic celebration system.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("miso.cogs.birthdays")


class Birthdays(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.birthday_check.start()

    def cog_unload(self):
        self.birthday_check.cancel()

    birthday_group = app_commands.Group(name="birthday", description="Birthday commands")

    @birthday_group.command(name="set", description="Set your birthday")
    @app_commands.describe(
        month="Birth month (1-12)",
        day="Birth day (1-31)",
        year="Birth year (optional, for age display)"
    )
    async def birthday_set(
        self,
        interaction: discord.Interaction,
        month: int,
        day: int,
        year: Optional[int] = None
    ) -> None:
        """Set your birthday."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.birthdays import set_birthday

        result = await set_birthday(interaction.guild.id, interaction.user.id, month, day, year)

        if result['success']:
            date_str = f"{month}/{day}"
            if year:
                age = datetime.now().year - year
                date_str += f"/{year} (You'll be {age + 1} on your next birthday!)"
            
            await interaction.followup.send(
                f"✅ Your birthday has been set to **{date_str}**!\n\n"
                "The server will celebrate your birthday automatically! 🎉",
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)

    @birthday_group.command(name="check", description="Check your or someone else's birthday")
    @app_commands.describe(user="User to check (leave empty for yourself)")
    async def birthday_check(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        """Check a birthday."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        target = user or interaction.user
        await interaction.response.defer(ephemeral=(user is None))

        from functions.birthdays import get_birthday

        birthday = await get_birthday(interaction.guild.id, target.id)

        if not birthday:
            if target.id == interaction.user.id:
                await interaction.followup.send(
                    "❌ You haven't set your birthday yet!\n\nUse `/birthday set` to set it.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ {target.mention} hasn't set their birthday yet.",
                    ephemeral=True
                )
            return

        month = birthday['birth_month']
        day = birthday['birth_day']
        year = birthday.get('birth_year')

        # Calculate age if year provided
        age_str = ""
        if year:
            age = datetime.now().year - year
            # Check if birthday has passed this year
            today = datetime.now()
            if today.month < month or (today.month == month and today.day < day):
                age -= 1
            age_str = f" (Age: {age})"

        # Calculate days until next birthday
        today = datetime.now().date()
        this_year_bday = datetime(today.year, month, day).date()
        if this_year_bday < today:
            next_bday = datetime(today.year + 1, month, day).date()
        else:
            next_bday = this_year_bday
        
        days_until = (next_bday - today).days

        embed = discord.Embed(
            title=f"🎂 {target.display_name}'s Birthday",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(
            name="Date",
            value=f"{month}/{day}{f'/{year}' if year else ''}{age_str}",
            inline=False
        )
        
        if days_until == 0:
            embed.add_field(name="Status", value="🎉 **IT'S TODAY!** 🎉", inline=False)
        elif days_until == 1:
            embed.add_field(name="Next Birthday", value="Tomorrow! 🎈", inline=False)
        else:
            embed.add_field(name="Next Birthday", value=f"In {days_until} days", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=(user is None))

    @birthday_group.command(name="remove", description="Remove your birthday")
    async def birthday_remove(self, interaction: discord.Interaction) -> None:
        """Remove your birthday."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.birthdays import delete_birthday

        success = await delete_birthday(interaction.guild.id, interaction.user.id)

        if success:
            await interaction.followup.send("✅ Your birthday has been removed.", ephemeral=True)
        else:
            await interaction.followup.send("❌ You don't have a birthday set!", ephemeral=True)

    # Admin commands
    @birthday_group.command(name="config", description="Configure birthday celebration settings (Admin only)")
    @app_commands.describe(
        enabled="Enable or disable birthday celebrations",
        channel="Channel for birthday announcements",
        message="Custom message template (use {user} for mention)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def birthday_config(
        self,
        interaction: discord.Interaction,
        enabled: Optional[bool] = None,
        channel: Optional[discord.TextChannel] = None,
        message: Optional[str] = None
    ) -> None:
        """Configure birthday settings."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.birthdays import get_birthday_settings, save_birthday_settings

        settings = await get_birthday_settings(interaction.guild.id)

        if enabled is not None:
            settings['enabled'] = enabled
        if channel is not None:
            settings['announcement_channel_id'] = channel.id
        if message is not None:
            settings['message_template'] = message

        success = await save_birthday_settings(interaction.guild.id, settings)

        if success:
            status = "enabled" if settings['enabled'] else "disabled"
            channel_mention = f"<#{settings['announcement_channel_id']}>" if settings['announcement_channel_id'] else "Not set"
            
            await interaction.followup.send(
                f"✅ Birthday settings updated!\n\n"
                f"**Status:** {status}\n"
                f"**Channel:** {channel_mention}\n"
                f"**Message:** {settings['message_template']}",
                ephemeral=True
            )
        else:
            await interaction.followup.send("❌ Failed to update settings.", ephemeral=True)

    @tasks.loop(hours=1)
    async def birthday_check(self):
        """Check for birthdays every hour and celebrate them."""
        try:
            from functions.birthdays import get_todays_birthdays, mark_birthday_celebrated, get_birthday_settings
            from functions.levels import add_xp_raw
            from functions.economy import add_coins

            for guild in self.bot.guilds:
                settings = await get_birthday_settings(guild.id)
                
                if not settings['enabled']:
                    continue
                
                if not settings['announcement_channel_id']:
                    continue
                
                channel = guild.get_channel(int(settings['announcement_channel_id']))
                if not channel:
                    continue
                
                birthdays = await get_todays_birthdays(guild.id)
                
                for birthday in birthdays:
                    try:
                        user_id = int(birthday['user_id'])
                        member = guild.get_member(user_id)
                        
                        if not member:
                            continue
                        
                        # Send celebration message
                        message = settings['message_template'].replace('{user}', member.mention)
                        
                        embed = discord.Embed(
                            title="🎉 Happy Birthday! 🎂",
                            description=message,
                            color=discord.Color.gold()
                        )
                        
                        # Calculate age if year is set
                        if birthday.get('birth_year'):
                            age = datetime.now().year - birthday['birth_year']
                            embed.add_field(name="Age", value=f"{age} years old! 🎈", inline=True)
                        
                        embed.set_thumbnail(url=member.display_avatar.url)
                        embed.set_footer(text="Have an amazing day!")
                        
                        await channel.send(embed=embed)
                        
                        # Award bonus XP and coins
                        try:
                            add_xp_raw(guild.id, user_id, settings['bonus_xp'])
                            await add_coins(guild.id, user_id, settings['bonus_coins'], 'birthday_bonus')
                            
                            # DM the user
                            try:
                                dm_embed = discord.Embed(
                                    title="🎂 Happy Birthday!",
                                    description=f"The {guild.name} server celebrated your birthday!\n\n"
                                               f"**Birthday Bonus:**\n"
                                               f"+{settings['bonus_xp']} XP\n"
                                               f"+{settings['bonus_coins']} coins",
                                    color=discord.Color.gold()
                                )
                                await member.send(embed=dm_embed)
                            except:
                                pass  # User has DMs disabled
                            
                        except Exception as e:
                            logger.error(f"Failed to award birthday bonus: {e}")
                        
                        # Mark as celebrated
                        await mark_birthday_celebrated(guild.id, user_id)
                        logger.info(f"Celebrated birthday for user {user_id} in guild {guild.id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to celebrate birthday: {e}", exc_info=True)
                        
        except Exception as e:
            logger.error(f"Birthday check task error: {e}", exc_info=True)

    @birthday_check.before_loop
    async def before_birthday_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    cog = Birthdays(bot)
    await bot.add_cog(cog)
    # Command groups are auto-registered by the cog, no need to manually add them
