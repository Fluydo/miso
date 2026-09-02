import time
import discord
from discord import app_commands
from discord.ext import commands

import config
from embeds.utility import (
    ping_embed,
    avatar_embed,
    user_info_embed,
    create_server_info_view,
    bot_info_embed,
)
from embeds.help import help_overview_embed, HelpView


class Utility(commands.Cog):
    """General server and bot utility commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="ping", description="Check the bot latency.")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        latency_ms = self.bot.latency * 1000
        embed = ping_embed(latency_ms)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="avatar", description="View full avatar of a user or yourself.")
    @app_commands.describe(user="The user whose avatar you want to view")
    async def avatar(
        self,
        interaction: discord.Interaction,
        user: discord.User | discord.Member | None = None,
    ) -> None:
        await interaction.response.defer()
        target = user or interaction.user
        embed = avatar_embed(target)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="userinfo", description="View detailed user profile and permission information.")
    @app_commands.describe(user="The member to view information for")
    @app_commands.guild_only()
    async def userinfo(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        await interaction.response.defer()
        target = user or (interaction.user if isinstance(interaction.user, discord.Member) else None)
        if not target:
            return

        embed = user_info_embed(target)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="serverinfo", description="View detailed information about this Discord server.")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not interaction.guild:
            return

        view = create_server_info_view(interaction.guild)
        await interaction.followup.send(view=view)

    @app_commands.command(name="botinfo", description="View information and performance statistics about Miso.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def botinfo(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        uptime = time.time() - self.start_time
        embed = bot_info_embed(self.bot, uptime)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="serverrules", description="Display official server guidelines and rules.")
    @app_commands.guild_only()
    async def serverrules(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not interaction.guild:
            return

        embed = discord.Embed(
            title=f"📜 {interaction.guild.name} — Server Rules",
            description=(
                "Please respect and adhere to all community guidelines:\n\n"
                f"{config.EMOJI_CHEVRON_RIGHT} **1. Be Respectful** — Treat all members and staff with courtesy. Harassment or hate speech is strictly prohibited.\n"
                f"{config.EMOJI_CHEVRON_RIGHT} **2. No Spam or Self-Promotion** — Keep chat clean and avoid unsolicited DMs or advertisement.\n"
                f"{config.EMOJI_CHEVRON_RIGHT} **3. Appropriate Content** — Post only in the designated channels. NSFW or harmful media is disallowed.\n"
                f"{config.EMOJI_CHEVRON_RIGHT} **4. Follow Staff Directions** — Moderators have final discretion on server enforcement.\n"
                f"{config.EMOJI_CHEVRON_RIGHT} **5. Discord ToS** — You must comply with all Discord Terms of Service and Community Guidelines."
            ),
            color=config.COLOR_PRIMARY,
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=f"{interaction.guild.name} Community Standards")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="supportticket", description="Quickly open a direct support inquiry.")
    @app_commands.guild_only()
    async def supportticket(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        from cogs.tickets import create_ticket_channel
        await interaction.response.defer(ephemeral=True)
        channel = await create_ticket_channel(
            guild=interaction.guild,
            member=interaction.user,
            ticket_type="support",
            bot=self.bot,
        )
        if channel:
            await interaction.followup.send(
                f"{config.EMOJI_TICK} Support ticket created! Head over to {channel.mention}.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Failed to create ticket channel. Please check server permissions.",
                ephemeral=True,
            )

    @app_commands.command(name="help", description="Browse all Miso commands by category.")
    async def help(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = help_overview_embed(self.bot)
        view = HelpView(self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="website", description="Visit the Miso Hub dashboard to manage giveaways, play games, and more!")
    async def website(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        embed = discord.Embed(
            title="🌐 Miso Hub Dashboard",
            description=(
                f"**Visit our web dashboard to:**\n"
                f"{config.EMOJI_CHEVRON_RIGHT} View and enter giveaways\n"
                f"{config.EMOJI_CHEVRON_RIGHT} Play casino games (Slots, Roulette, Crash)\n"
                f"{config.EMOJI_CHEVRON_RIGHT} Check leaderboards and your stats\n"
                f"{config.EMOJI_CHEVRON_RIGHT} Manage your profile and coins\n\n"
                f"**[Click here to open Miso Hub →](https://miso-dashboard-iota.vercel.app/)**"
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_footer(text=f"{config.BOT_NAME} Web Dashboard")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
