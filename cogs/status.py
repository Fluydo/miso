import discord
from discord import app_commands
from discord.ext import commands

from embeds.status import user_status_embed


class Status(commands.Cog):
    """User status inspection commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="userstatus", description="Display detailed profile and presence status for a user.")
    @app_commands.describe(user="The member to inspect (defaults to yourself)")
    @app_commands.guild_only()
    async def userstatus(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        target = user or (interaction.user if isinstance(interaction.user, discord.Member) else None)
        if not target:
            return

        embed = user_status_embed(target)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Status(bot))
