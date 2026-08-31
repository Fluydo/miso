"""
cogs/tickets.py
Discord Ticket System Cog for Miso Bot.

Features:
- Components V2 Ticket Creation Panel with custom dropdown options.
- Automated channel provisioning with strict permission overwrites.
- In-channel ticket controls (Close, Claim, Transcripts).
- Management slash commands (/ticket panel, /ticket add, /ticket remove, /ticket close, /ticket category).
"""

import asyncio
import io
import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import LayoutView, Container, TextDisplay, Separator

import config
from functions.permissions import is_moderator
from functions.tickets import (
    claim_ticket,
    get_guild_ticket_config,
    get_ticket_info,
    register_new_ticket,
    remove_ticket_record,
    set_ticket_category,
)
from embeds.tickets import (
    TICKET_TYPES,
    TicketPanelSelect,
    CloseTicketButton,
    ClaimTicketButton,
    create_ticket_panel_view,
    create_ticket_welcome_view,
)
from functions.moderation import send_mod_log

logger = logging.getLogger("miso.cogs.tickets")


class ConfirmCloseView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel, user: discord.User | discord.Member) -> None:
        super().__init__(timeout=60)
        self.channel = channel
        self.closed_by = user

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        cog = interaction.client.get_cog("Tickets")
        if cog:
            await cog.execute_close_ticket(interaction, self.channel, self.closed_by)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Ticket closure cancelled.", view=None)


class Tickets(commands.Cog):
    """Support & Staff Application Ticket System."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # NOTE: LayoutView (Components V2) is NOT registerable as a persistent view.
        # Ticket panel callbacks route through the Cog via get_cog('Tickets'), so no add_view needed.

    ticket_group = app_commands.Group(
        name="ticket",
        description="Ticket management and configuration commands",
    )

    # ==========================================
    # /TICKET PANEL
    # ==========================================
    @ticket_group.command(name="panel", description="Send the Components V2 Support & Application ticket panel.")
    @app_commands.describe(channel="The channel where the ticket panel will be sent")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def send_panel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Ticket panels must be sent in a text channel.",
                ephemeral=True,
            )
            return

        panel_view = create_ticket_panel_view()
        await target_channel.send(view=panel_view)

        await interaction.response.send_message(
            f"{config.EMOJI_TICK} Ticket panel successfully sent to {target_channel.mention}!",
            ephemeral=True,
        )

    # ==========================================
    # /TICKET CATEGORY
    # ==========================================
    @ticket_group.command(name="category", description="Set the category under which new tickets are created.")
    @app_commands.describe(category="The category channel for tickets")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:
        if not interaction.guild:
            return

        await interaction.response.defer(ephemeral=True)

        set_ticket_category(interaction.guild_id, category.id)

        # Lock the category from @everyone so tickets are private by default
        everyone = interaction.guild.default_role
        try:
            await category.set_permissions(
                everyone,
                view_channel=False,
                read_messages=False,
                reason="Ticket category locked — tickets are private by default",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"{config.EMOJI_WARN} Category saved, but I'm missing permissions to update the category overwrites. "
                f"Please manually set `@everyone` to **Cannot view** on **{category.name}**.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"{config.EMOJI_TICK} Ticket category set to **{category.name}**.\n"
            f"`@everyone` has been denied view access on the category — tickets will be private by default.",
            ephemeral=True,
        )

    # ==========================================
    # /TICKET ADD
    # ==========================================
    @ticket_group.command(name="add", description="Add a member to the current ticket channel.")
    @app_commands.describe(user="The member to add to this ticket")
    async def add_member(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not is_moderator(interaction.user):
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} You need Manage Messages permissions to add members.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await channel.set_permissions(user, read_messages=True, send_messages=True, attach_files=True)
        await interaction.response.send_message(
            f"{config.EMOJI_TICK} Added {user.mention} to this ticket.",
        )

    # ==========================================
    # /TICKET REMOVE
    # ==========================================
    @ticket_group.command(name="remove", description="Remove a member from the current ticket channel.")
    @app_commands.describe(user="The member to remove from this ticket")
    async def remove_member(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not is_moderator(interaction.user):
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} You need Manage Messages permissions to remove members.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(
            f"{config.EMOJI_TICK} Removed {user.mention} from this ticket.",
        )

    # ==========================================
    # /TICKET CLOSE
    # ==========================================
    @ticket_group.command(name="close", description="Close the current ticket channel.")
    @app_commands.describe(reason="Optional reason for closing the ticket")
    async def close_command(
        self,
        interaction: discord.Interaction,
        reason: Optional[str] = "No reason provided",
    ) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await self.prompt_close_ticket(interaction)

    # ==========================================
    # TICKET CREATION LOGIC
    # ==========================================
    async def handle_ticket_creation(self, interaction: discord.Interaction, ticket_type: str) -> None:
        guild = interaction.guild
        user = interaction.user
        if not guild:
            return

        info = TICKET_TYPES.get(ticket_type, TICKET_TYPES["support"])
        prefix = info["prefix"]

        # Check existing active tickets for user in this category
        cfg = get_guild_ticket_config(guild.id)
        for ch_id_str, t_meta in cfg.get("active_tickets", {}).items():
            if t_meta.get("user_id") == user.id and t_meta.get("type") == ticket_type:
                existing_ch = guild.get_channel(int(ch_id_str))
                if existing_ch:
                    await interaction.response.send_message(
                        f"{config.EMOJI_WARN} You already have an open ticket: {existing_ch.mention}",
                        ephemeral=True,
                    )
                    return

        # Prepare permissions
        category_id = cfg.get("category_id")
        category = guild.get_channel(category_id) if category_id else None
        if not isinstance(category, discord.CategoryChannel):
            category = None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True,
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_permissions=True,
                read_message_history=True,
            ),
        }

        # Add staff roles if present
        for role in guild.roles:
            if role.permissions.manage_messages or role.permissions.manage_guild or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True,
                )

        channel_name = f"{prefix}-{user.name[:15]}"
        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"{info['label']} ticket for {user.name} ({user.id})",
            )
        except Exception as e:
            logger.error(f"Failed to create ticket channel: {e}", exc_info=True)
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Failed to create ticket channel. Please ensure the bot has **Manage Channels** permission.",
                ephemeral=True,
            )
            return

        ticket_num = register_new_ticket(guild.id, ticket_channel.id, user.id, ticket_type)

        welcome_view = create_ticket_welcome_view(user, ticket_type, ticket_num)
        await ticket_channel.send(view=welcome_view)

        await interaction.response.send_message(
            f"{config.EMOJI_TICK} Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True,
        )

    # ==========================================
    # TICKET ACTION HANDLERS
    # ==========================================
    async def prompt_close_ticket(self, interaction: discord.Interaction) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        view = ConfirmCloseView(channel, interaction.user)
        await interaction.response.send_message(
            "⚠️ **Are you sure you want to close this ticket?**",
            view=view,
            ephemeral=True,
        )

    async def execute_close_ticket(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        closed_by: discord.User | discord.Member,
    ) -> None:
        guild = channel.guild
        ticket_info = remove_ticket_record(guild.id, channel.id)

        await interaction.response.send_message(
            f"{config.EMOJI_WARN} Ticket will close and delete in **5 seconds**...",
        )

        # Generate text transcript
        messages = []
        async for msg in channel.history(limit=500, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(f"[{timestamp}] {msg.author.name} ({msg.author.id}): {msg.content}")

        transcript_text = "\n".join(messages)
        transcript_file = discord.File(
            io.BytesIO(transcript_text.encode("utf-8")),
            filename=f"transcript-{channel.name}.txt",
        )

        # Send log to moderation forum / channel
        log_embed = discord.Embed(
            title=f"{config.EMOJI_TICKET} Ticket Closed",
            color=config.COLOR_ERROR,
            timestamp=datetime.now(timezone.utc),
        )
        log_embed.add_field(name="Ticket", value=f"`#{channel.name}`", inline=True)
        log_embed.add_field(name="Closed By", value=f"{closed_by.mention} (`{closed_by.id}`)", inline=True)
        if ticket_info:
            creator = guild.get_member(ticket_info.get("user_id", 0))
            creator_str = creator.mention if creator else f"`{ticket_info.get('user_id')}`"
            log_embed.add_field(name="Ticket Creator", value=creator_str, inline=True)
            log_embed.add_field(name="Type", value=f"`{ticket_info.get('type', 'support')}`", inline=True)

        await send_mod_log(guild, embed=log_embed, file=transcript_file, log_type="moderation")

        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {closed_by.name}")
        except Exception as e:
            logger.error(f"Error deleting ticket channel: {e}")

    async def handle_claim_ticket(self, interaction: discord.Interaction) -> None:
        if not is_moderator(interaction.user):
            await interaction.response.send_message(
                f"{config.EMOJI_CROSS} Only staff members can claim tickets.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        claimed = claim_ticket(interaction.guild_id, channel.id, interaction.user.id)
        if claimed:
            await interaction.response.send_message(
                f"{config.EMOJI_TICK} Ticket has been claimed by {interaction.user.mention}!",
            )
        else:
            await interaction.response.send_message(
                f"{config.EMOJI_INFO} Ticket claim recorded for {interaction.user.mention}.",
            )


async def create_ticket_channel(
    guild: discord.Guild,
    member: discord.User | discord.Member,
    ticket_type: str,
    bot: commands.Bot,
) -> Optional[discord.TextChannel]:
    """Standalone helper to create a ticket channel — used by /supportticket in utility.py."""
    cog = bot.get_cog("Tickets")
    if not cog:
        return None

    # Check for existing open ticket
    cfg = get_guild_ticket_config(guild.id)
    for ch_id_str, t_meta in cfg.get("active_tickets", {}).items():
        if t_meta.get("user_id") == member.id and t_meta.get("type") == ticket_type:
            existing = guild.get_channel(int(ch_id_str))
            if existing:
                return existing  # type: ignore

    info = TICKET_TYPES.get(ticket_type, TICKET_TYPES["support"])
    prefix = info["prefix"]

    category_id = cfg.get("category_id")
    category = guild.get_channel(category_id) if category_id else None
    if not isinstance(category, discord.CategoryChannel):
        category = None

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        member: discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            attach_files=True, embed_links=True, read_message_history=True,
        ),
        guild.me: discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            manage_channels=True, manage_permissions=True, read_message_history=True,
        ),
    }
    for role in guild.roles:
        if role.permissions.manage_messages or role.permissions.manage_guild or role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True,
                attach_files=True, embed_links=True, read_message_history=True,
            )

    try:
        ticket_channel = await guild.create_text_channel(
            name=f"{prefix}-{member.name[:15]}",
            category=category,
            overwrites=overwrites,
            topic=f"{info['label']} ticket for {member.name} ({member.id})",
        )
    except Exception:
        return None

    ticket_num = register_new_ticket(guild.id, ticket_channel.id, member.id, ticket_type)
    welcome_view = create_ticket_welcome_view(member, ticket_type, ticket_num)
    await ticket_channel.send(view=welcome_view)
    return ticket_channel


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
