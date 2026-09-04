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
from functions.time_parser import format_duration, parse_duration

WEBSITE_URL = "https://miso-dashboard-iota.vercel.app"


class GiveawayRedeemButton(discord.ui.Button):
    """Button for winners to redeem their prize within 24 hours."""
    def __init__(self, message_id: int, winner_id: int, expires_ts: int) -> None:
        super().__init__(
            label="Redeem Prize",
            style=discord.ButtonStyle.success,
            emoji="🎁",
            custom_id=f"giveaway_redeem_{message_id}",
        )
        self.target_message_id = message_id
        self.winner_id = winner_id
        self.expires_ts = expires_ts

    async def callback(self, interaction: discord.Interaction) -> None:
        # Only winner can redeem
        if interaction.user.id != self.winner_id:
            await interaction.response.send_message(
                "❌ Only the winner can redeem this prize!",
                ephemeral=True
            )
            return
        
        # Check if already redeemed
        from functions.giveaways import load_giveaways, save_giveaways
        data = load_giveaways()
        giveaway = data.get(str(self.target_message_id))
        
        if not giveaway:
            await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
            return
        
        if giveaway.get("redeemed"):
            await interaction.response.send_message("✅ Prize already redeemed!", ephemeral=True)
            return
        
        # Check if expired
        now = datetime.now(timezone.utc).timestamp()
        if now > self.expires_ts:
            await interaction.response.send_message("❌ Redemption period has expired.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Create ticket using ticket system
        from functions.tickets import register_new_ticket, get_guild_ticket_config
        
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ Could not access guild.", ephemeral=True)
            return
        
        ticket_config = get_guild_ticket_config(guild.id)
        category_id = ticket_config.get("category_id")
        
        if not category_id:
            await interaction.followup.send(
                "❌ Ticket system not configured. Please ask an admin to set up `/ticket category` first.",
                ephemeral=True
            )
            return
        
        category = guild.get_channel(category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("❌ Ticket category not found.", ephemeral=True)
            return
        
        # Create ticket channel
        prize = giveaway.get("prize", "Prize")
        ticket_name = f"giveaway-{prize[:20].replace(' ', '-').lower()}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        
        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites,
                topic=f"Giveaway Redemption Ticket | Winner: {interaction.user.name} | Prize: {prize}"
            )
        except Exception as e:
            logger.error(f"Failed to create redemption ticket: {e}")
            await interaction.followup.send("❌ Failed to create ticket channel.", ephemeral=True)
            return
        
        # Register ticket
        ticket_num = register_new_ticket(
            guild_id=guild.id,
            channel_id=ticket_channel.id,
            user_id=interaction.user.id,
            ticket_type="giveaway_redemption"
        )
        
        # Update giveaway data
        giveaway["redeemed"] = True
        giveaway["redeemed_at"] = datetime.now(timezone.utc).isoformat()
        giveaway["ticket_id"] = str(ticket_channel.id)
        save_giveaways(data)
        
        # Send ticket welcome message
        embed = discord.Embed(
            title=f"🎁 Giveaway Prize Redemption - Ticket #{ticket_num}",
            description=(
                f"**Winner:** {interaction.user.mention}\n"
                f"**Prize:** `{prize}`\n"
                f"**Giveaway Host:** <@{giveaway.get('host_id')}>\n\n"
                f"A staff member will assist you with your prize shortly!"
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_footer(text=f"{config.BOT_NAME} Giveaway Redemption")
        
        await ticket_channel.send(f"{interaction.user.mention} <@{giveaway.get('host_id')}>", embed=embed)
        
        # Update original message to show redeemed
        await interaction.followup.send(
            f"✅ Prize redeemed! Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )
        
        # Disable buttons
        self.disabled = True
        try:
            view: discord.ui.View = self.view  # type: ignore
            await interaction.message.edit(view=view)
        except Exception:
            pass


class GiveawayRerollButton(discord.ui.Button):
    """Button for moderators to reroll the giveaway."""
    def __init__(self, message_id: int) -> None:
        super().__init__(
            label="Reroll Winner",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            custom_id=f"giveaway_reroll_{message_id}",
        )
        self.target_message_id = message_id

    async def callback(self, interaction: discord.Interaction) -> None:
        # Check if user has manage_guild permission
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Only moderators can reroll giveaways!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        from functions.giveaways import reroll_giveaway_redemption
        new_winner, prize, expires_ts = reroll_giveaway_redemption(self.target_message_id)
        
        if not new_winner:
            await interaction.followup.send(f"❌ {prize}", ephemeral=True)
            return
        
        # Send new winner announcement
        embed = discord.Embed(
            title="🎁 GIVEAWAY REROLLED 🎁",
            description=(
                f"🎉 **New Winner:** <@{new_winner}>!\n"
                f"**Prize:** `{prize}`\n\n"
                f"You have **24 hours** to redeem your prize (<t:{expires_ts}:R>)\n"
                f"Click the button below to create a redemption ticket!"
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_footer(text=f"{config.BOT_NAME} Giveaways")
        
        # Create new view with redeem and reroll buttons
        view = discord.ui.View(timeout=None)
        view.add_item(GiveawayRedeemButton(self.target_message_id, new_winner, expires_ts))
        view.add_item(GiveawayRerollButton(self.target_message_id))
        
        await interaction.followup.send(f"<@{new_winner}>", embed=embed, view=view)
        
        # Try to DM the winner
        try:
            user = await interaction.client.fetch_user(new_winner)
            dm_embed = discord.Embed(
                title="🎉 You Won a Giveaway!",
                description=(
                    f"**Prize:** `{prize}`\n"
                    f"**Server:** {interaction.guild.name}\n\n"
                    f"You have **24 hours** to redeem (<t:{expires_ts}:R>)\n"
                    f"Check the giveaway channel to redeem your prize!"
                ),
                color=config.COLOR_PRIMARY,
            )
            await user.send(embed=dm_embed)
        except Exception as e:
            logger.warning(f"Could not DM reroll winner {new_winner}: {e}")


class GiveawayRedemptionView(discord.ui.View):
    """View with Redeem and Reroll buttons for giveaway winners."""
    def __init__(self, message_id: int, winner_id: int, expires_ts: int) -> None:
        super().__init__(timeout=None)
        self.add_item(GiveawayRedeemButton(message_id, winner_id, expires_ts))
        self.add_item(GiveawayRerollButton(message_id))


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
        
        # Load giveaway data to check requirements
        from functions.giveaways import load_giveaways
        data = load_giveaways()
        giveaway = data.get(str(self.target_message_id))
        
        if not giveaway or giveaway.get("ended"):
            await interaction.followup.send("❌ This giveaway has ended.", ephemeral=True)
            return
        
        # Check requirements
        requirements = giveaway.get("requirements", {})
        
        # Check minimum invites requirement
        if requirements.get("min_invites"):
            from functions.invites import get_invite_stats
            guild_id = interaction.guild_id
            user_id = interaction.user.id
            stats = get_invite_stats(guild_id, user_id)
            
            # Calculate active invites (joined - left)
            active_invites = stats.get("joins", 0) - stats.get("leaves", 0)
            min_required = requirements["min_invites"]
            
            if active_invites < min_required:
                await interaction.followup.send(
                    f"❌ You need at least **{min_required}** active invite{'s' if min_required > 1 else ''} to enter this giveaway.\n"
                    f"You currently have **{active_invites}** active invite{'s' if active_invites != 1 else ''}.",
                    ephemeral=True
                )
                return
        
        # Check required roles
        if requirements.get("required_roles"):
            required_role_ids = [int(r) for r in requirements["required_roles"]]
            user_role_ids = [role.id for role in interaction.user.roles]
            
            has_required_role = any(rid in user_role_ids for rid in required_role_ids)
            if not has_required_role:
                role_mentions = ", ".join([f"<@&{rid}>" for rid in required_role_ids])
                await interaction.followup.send(
                    f"❌ You need one of these roles to enter: {role_mentions}",
                    ephemeral=True
                )
                return
        
        # Requirements met, proceed with entry
        is_added, count = add_entry(self.target_message_id, interaction.user.id)
        self.label = f"Enter ({count})"

        # Sync to Supabase - TODO: Re-implement if needed
        # asyncio.create_task(sync_giveaway_entry_to_supabase(self.target_message_id, interaction.user.id, is_added))

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
            label="Website",
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
            # Check for ended giveaways
            if not g.get("ended"):
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
                        winner_id = winners[0] if len(winners) == 1 else None
                        winners_mentions = ", ".join([f"<@{uid}>" for uid in winners])
                        
                        # Set 24h redemption expiry
                        expires_ts = int(now + 86400)  # 24 hours from now
                        
                        # Update giveaway with winner and expiry
                        record["winner_id"] = winner_id
                        record["redemption_expires"] = expires_ts
                        from functions.giveaways import save_giveaways
                        save_giveaways(data)
                        
                        desc = (
                            f"🎉 **Winner:** {winners_mentions}!\n"
                            f"**Prize:** `{record['prize']}`\n\n"
                            f"You have **24 hours** to redeem your prize (<t:{expires_ts}:R>)\n"
                            f"Click the button below to create a redemption ticket!"
                        )
                    else:
                        desc = "No valid entries were submitted for this giveaway."
                        expires_ts = None
                        winner_id = None

                    end_embed = discord.Embed(
                        title="🎁 GIVEAWAY ENDED 🎁",
                        description=desc,
                        color=config.COLOR_PRIMARY,
                    )
                    end_embed.set_footer(text=f"Hosted by <@{record['host_id']}> • {config.BOT_NAME} Giveaways")

                    # Create view based on whether there are winners
                    if winners and winner_id and expires_ts:
                        # Redemption view with Redeem and Reroll buttons
                        view = GiveawayRedemptionView(mid, winner_id, expires_ts)
                        await msg.edit(embed=end_embed, view=view)
                        
                        # Send announcement with winner mention
                        await channel.send(f"<@{winner_id}>", embed=end_embed, view=view)
                        
                        # Try to DM the winner
                        try:
                            winner_user = await self.bot.fetch_user(winner_id)
                            dm_embed = discord.Embed(
                                title="🎉 You Won a Giveaway!",
                                description=(
                                    f"**Prize:** `{record['prize']}`\n"
                                    f"**Server:** {guild.name}\n\n"
                                    f"You have **24 hours** to redeem (<t:{expires_ts}:R>)\n"
                                    f"Check the giveaway channel to redeem your prize!"
                                ),
                                color=config.COLOR_PRIMARY,
                            )
                            await winner_user.send(embed=dm_embed)
                            record["dm_sent"] = True
                            from functions.giveaways import save_giveaways
                            save_giveaways(data)
                        except Exception as e:
                            logger.warning(f"Could not DM winner {winner_id}: {e}")
                    else:
                        # No winners - disable button
                        view = discord.ui.View(timeout=None)
                        btn = discord.ui.Button(
                            label=f"Ended ({len(record.get('entries', []))})",
                            style=discord.ButtonStyle.secondary,
                            emoji="🎉",
                            disabled=True,
                        )
                        view.add_item(btn)
                        await msg.edit(embed=end_embed, view=view)
            
            # Check for expired redemptions
            elif g.get("ended") and not g.get("redeemed"):
                redemption_expires = g.get("redemption_expires")
                if redemption_expires and now >= redemption_expires:
                    winner_id = g.get("winner_id")
                    if not winner_id:
                        continue
                    
                    # Send expiry DM if not already sent
                    if not g.get("expiry_dm_sent"):
                        try:
                            winner_user = await self.bot.fetch_user(winner_id)
                            expiry_embed = discord.Embed(
                                title="⏰ Giveaway Prize Redemption Expired",
                                description=(
                                    f"**Prize:** `{g.get('prize', 'Prize')}`\n"
                                    f"**Server:** {self.bot.get_guild(g.get('guild_id')).name if self.bot.get_guild(g.get('guild_id')) else 'Unknown'}\n\n"
                                    f"You did not redeem your prize within 24 hours.\n"
                                    f"The prize may be rerolled to another participant."
                                ),
                                color=0xFF6B6B,
                            )
                            await winner_user.send(embed=expiry_embed)
                            g["expiry_dm_sent"] = True
                            from functions.giveaways import save_giveaways
                            save_giveaways(data)
                        except Exception as e:
                            logger.warning(f"Could not DM expired winner {winner_id}: {e}")

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
        min_invites="Minimum invites required to enter (optional)",
        required_role="Role required to enter (optional)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_start(
        self,
        interaction: discord.Interaction,
        duration: str,
        prize: str,
        winners: app_commands.Range[int, 1, 20] = 1,
        min_invites: app_commands.Range[int, 1, 100] | None = None,
        required_role: discord.Role | None = None,
    ) -> None:
        if not interaction.guild:
            return

        try:
            td = parse_duration(duration)
        except ValueError as e:
            await interaction.response.defer()
            await interaction.followup.send(f"{config.EMOJI_CROSS} {e}", ephemeral=True)
            return

        end_ts = datetime.now(timezone.utc).timestamp() + td.total_seconds()
        formatted_dur = format_duration(td)

        # Build requirements text
        req_text = ""
        if min_invites or required_role:
            req_text = "\n**Requirements:**\n"
            if min_invites:
                req_text += f"• Minimum {min_invites} invite{'s' if min_invites > 1 else ''}\n"
            if required_role:
                req_text += f"• Have {required_role.mention} role\n"

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=(
                f"**Prize:** `{prize}`\n"
                f"**Winners:** `{winners}`\n"
                f"**Ends in:** `{formatted_dur}` (<t:{int(end_ts)}:R>)\n"
                f"**Hosted by:** {interaction.user.mention}"
                f"{req_text}\n"
                f"Click the button below to enter!"
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_footer(text=f"{config.BOT_NAME} Giveaways • Good luck!")

        # Initial message
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()

        create_giveaway(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            message_id=msg.id,
            prize=prize,
            winners_count=winners,
            end_timestamp=end_ts,
            host_id=interaction.user.id,
            min_invites=min_invites,
            required_roles=[required_role.id] if required_role else None,
        )

        # Sync to Supabase - TODO: Re-implement if needed
        # asyncio.create_task(sync_giveaway_to_supabase(...))

        view = GiveawayView(message_id=msg.id, count=0)
        await msg.edit(view=view)

    @giveaway_group.command(name="reroll", description="Reroll a new winner for an ended giveaway.")
    @app_commands.describe(message_id="The message ID of the giveaway")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str) -> None:
        if not interaction.guild:
            return

        if not message_id.strip().isdigit():
            await interaction.response.defer()
            await interaction.followup.send(f"{config.EMOJI_CROSS} Invalid message ID.", ephemeral=True)
            return

        mid = int(message_id.strip())
        new_winner, prize = reroll_giveaway(mid)

        if not new_winner:
            await interaction.response.defer()
            await interaction.followup.send(f"{config.EMOJI_CROSS} {prize}", ephemeral=True)
            return

        await interaction.response.defer()
        await interaction.followup.send(
            f"🎉 **Reroll!** The new winner for **{prize}** is <@{new_winner}>! Congratulations!"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
