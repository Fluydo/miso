"""
cogs/giveaways.py
Interactive Giveaway System for Miso Bot with Components V2 buttons and live timers.
"""

import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from functions.giveaways import (
    add_entry,
    create_giveaway,
    end_giveaway,
    load_giveaways,
    reroll_giveaway,
)
from functions.supabase_sync import sync_giveaway_to_supabase, sync_giveaway_entry_to_supabase
from functions.time_parser import format_duration, parse_duration

WEBSITE_URL = "https://miso-dashboard-iota.vercel.app"


class GiveawayJoinButton(discord.ui.Button):
    def __init__(self, message_id: int, count: int = 0) -> None:
        super().__init__(
            label=f"Enter ({count})",
            style=discord.ButtonStyle.primary,
            emoji="🎉",
            custom_id=f"giveaway_enter_{message_id}",
        )
        self.target_message_id = message_id

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        is_added, count = add_entry(self.target_message_id, interaction.user.id)
        self.label = f"Enter ({count})"

        # Sync to Supabase
        asyncio.create_task(sync_giveaway_entry_to_supabase(self.target_message_id, interaction.user.id, is_added))

        if is_added:
            await interaction.followup.send("🎉 You have entered the giveaway! Good luck!", ephemeral=True)
        else:
            await interaction.followup.send("❌ You left the giveaway.", ephemeral=True)

        try:
            view: discord.ui.View = self.view  # type: ignore
            await interaction.message.edit(view=view)
        except Exception:
            pass


class GiveawayView(discord.ui.View):
    def __init__(self, message_id: int, count: int = 0) -> None:
        super().__init__(timeout=None)
        self.add_item(GiveawayJoinButton(message_id, count))
        self.add_item(discord.ui.Button(
            label="Website: Click Me!",
            style=discord.ButtonStyle.link,
            emoji="🌐",
            url=f"{WEBSITE_URL}/giveaways/{message_id}",
        ))


class Giveaways(commands.Cog):
    """Host and manage server giveaways."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.giveaway_checker.start()

    def cog_unload(self) -> None:
        self.giveaway_checker.cancel()

    @tasks.loop(seconds=15)
    async def giveaway_checker(self) -> None:
        """Background task checking if any active giveaway timer has expired."""
        data = load_giveaways()
        now = datetime.now(timezone.utc).timestamp()

        for mid_str, g in list(data.items()):
            if g.get("ended"):
                continue

            end_ts = g.get("end_timestamp", 0)
            if now >= end_ts:
                mid = int(mid_str)
                record = end_giveaway(mid)
                if not record:
                    continue

                guild = self.bot.get_guild(record["guild_id"])
                if not guild:
                    continue

                channel = guild.get_channel(record["channel_id"])
                if not channel or not isinstance(channel, discord.TextChannel):
                    continue

                try:
                    msg = await channel.fetch_message(mid)
                except Exception:
                    continue

                winners = record.get("winners", [])
                if winners:
                    winners_mentions = ", ".join([f"<@{uid}>" for uid in winners])
                    desc = f"🎉 Congratulations {winners_mentions}!\nYou won **{record['prize']}**!"
                else:
                    desc = "No valid entries were submitted for this giveaway."

                # Sync ended status to Supabase
                asyncio.create_task(
                    sync_giveaway_to_supabase(
                        message_id=mid,
                        guild_id=record["guild_id"],
                        channel_id=record["channel_id"],
                        prize=record["prize"],
                        winners_count=record["winners_count"],
                        end_timestamp=record["end_timestamp"],
                        host_id=record["host_id"],
                        active=False,
                        winner_discord_id=str(winners[0]) if winners else None,
                    )
                )

                end_embed = discord.Embed(
                    title="🎁 GIVEAWAY ENDED 🎁",
                    description=desc,
                    color=config.COLOR_PRIMARY,
                )
                end_embed.set_footer(text=f"Hosted by <@{record['host_id']}> • {config.BOT_NAME} Giveaways")

                # Disable button
                view = discord.ui.View(timeout=None)
                btn = discord.ui.Button(
                    label=f"Ended ({len(record.get('entries', []))})",
                    style=discord.ButtonStyle.secondary,
                    emoji="🎉",
                    disabled=True,
                )
                view.add_item(btn)

                await msg.edit(embed=end_embed, view=view)
                if winners:
                    await channel.send(f"🎉 Congratulations {winners_mentions}! You won **{record['prize']}**!")

    @giveaway_checker.before_loop
    async def before_giveaway_checker(self) -> None:
        await self.bot.wait_until_ready()

    giveaway_group = app_commands.Group(
        name="giveaway",
        description="Host, end, or reroll giveaways.",
        guild_only=True,
    )

    @giveaway_group.command(name="start", description="Start a new interactive server giveaway.")
    @app_commands.describe(
        duration="Duration of the giveaway (e.g. 10m, 1h, 1d)",
        prize="The prize to be given away",
        winners="Number of winners (default 1)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_start(
        self,
        interaction: discord.Interaction,
        duration: str,
        prize: str,
        winners: app_commands.Range[int, 1, 20] = 1,
    ) -> None:
        if not interaction.guild:
            return

        try:
            td = parse_duration(duration)
        except ValueError as e:
            await interaction.response.send_message(f"{config.EMOJI_CROSS} {e}", ephemeral=True)
            return

        end_ts = datetime.now(timezone.utc).timestamp() + td.total_seconds()
        formatted_dur = format_duration(td)

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=(
                f"**Prize:** `{prize}`\n"
                f"**Winners:** `{winners}`\n"
                f"**Ends in:** `{formatted_dur}` (<t:{int(end_ts)}:R>)\n"
                f"**Hosted by:** {interaction.user.mention}\n\n"
                f"Click the button below to enter!"
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_footer(text=f"{config.BOT_NAME} Giveaways • Good luck!")

        # Initial message
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        create_giveaway(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            message_id=msg.id,
            prize=prize,
            winners_count=winners,
            end_timestamp=end_ts,
            host_id=interaction.user.id,
        )

        # Sync to Supabase
        asyncio.create_task(
            sync_giveaway_to_supabase(
                message_id=msg.id,
                guild_id=interaction.guild.id,
                channel_id=interaction.channel_id,
                prize=prize,
                winners_count=winners,
                end_timestamp=end_ts,
                host_id=interaction.user.id,
                active=True,
            )
        )

        view = GiveawayView(message_id=msg.id, count=0)
        await msg.edit(view=view)

    @giveaway_group.command(name="reroll", description="Reroll a new winner for an ended giveaway.")
    @app_commands.describe(message_id="The message ID of the giveaway")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str) -> None:
        if not interaction.guild:
            return

        if not message_id.strip().isdigit():
            await interaction.response.send_message(f"{config.EMOJI_CROSS} Invalid message ID.", ephemeral=True)
            return

        mid = int(message_id.strip())
        new_winner, prize = reroll_giveaway(mid)

        if not new_winner:
            await interaction.response.send_message(f"{config.EMOJI_CROSS} {prize}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"🎉 **Reroll!** The new winner for **{prize}** is <@{new_winner}>! Congratulations!"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
