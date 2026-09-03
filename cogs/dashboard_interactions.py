"""
Dashboard Interactions Cog
Handles button/select menu interactions for components created via dashboard
"""

import logging
import discord
from discord.ext import commands

logger = logging.getLogger("miso.dashboard_interactions")


class DashboardInteractions(commands.Cog):
    """Handle interactions from dashboard-created components."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle all interactions from dashboard components."""
        
        # Only handle component interactions (buttons, selects)
        if interaction.type not in (discord.InteractionType.component, discord.InteractionType.modal_submit):
            return
        
        # Get custom_id
        custom_id = interaction.data.get("custom_id", "")
        
        # Check if this is a dashboard-created component
        if not custom_id:
            return
        
        # Parse action type from custom_id format: "action_uuid"
        parts = custom_id.split("_", 1)
        if len(parts) < 2:
            return
        
        action_type = parts[0]
        component_id = parts[1] if len(parts) > 1 else ""
        
        logger.info(f"Dashboard interaction: {action_type} from {interaction.user} in {interaction.guild}")
        
        # Route to appropriate handler
        try:
            if action_type == "create":
                await self.handle_create_ticket(interaction)
            elif action_type == "url":
                # URL buttons are handled by Discord, shouldn't reach here
                pass
            elif action_type == "role":
                await self.handle_role_action(interaction, component_id)
            elif action_type == "select":
                await self.handle_select_menu(interaction)
            elif action_type == "custom":
                await self.handle_custom_action(interaction, component_id)
            else:
                # Unknown action type, send generic response
                await interaction.response.send_message(
                    f"✅ Button clicked! Action: {action_type}",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error handling dashboard interaction {custom_id}: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while processing this interaction.",
                    ephemeral=True
                )

    async def handle_create_ticket(self, interaction: discord.Interaction):
        """Handle ticket creation button from dashboard."""
        # Check if tickets cog exists
        tickets_cog = self.bot.get_cog("Tickets")
        
        if not tickets_cog:
            await interaction.response.send_message(
                "❌ Ticket system is not enabled on this server.",
                ephemeral=True
            )
            return
        
        # Import ticket creation logic
        from functions.tickets import get_guild_ticket_config, register_new_ticket
        from embeds.tickets import create_ticket_welcome_view
        
        guild = interaction.guild
        if not guild:
            return
        
        # Get ticket config
        config = get_guild_ticket_config(str(guild.id))
        category_id = config.get("category_id")
        
        if not category_id:
            await interaction.response.send_message(
                "❌ Ticket category not configured. Please ask an administrator to set it up with `/ticket category`.",
                ephemeral=True
            )
            return
        
        category = guild.get_channel(int(category_id))
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ Ticket category not found. Please contact an administrator.",
                ephemeral=True
            )
            return
        
        # Check if user already has a ticket
        existing_ticket = discord.utils.find(
            lambda ch: isinstance(ch, discord.TextChannel) and ch.category == category and f"ticket-{interaction.user.id}" in ch.name,
            guild.channels
        )
        
        if existing_ticket:
            await interaction.response.send_message(
                f"⚠️ You already have an open ticket: {existing_ticket.mention}",
                ephemeral=True
            )
            return
        
        # Create ticket channel
        await interaction.response.defer(ephemeral=True)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            )
        }
        
        ticket_channel = await category.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            topic=f"Support ticket for {interaction.user} (ID: {interaction.user.id})"
        )
        
        # Register ticket in database
        register_new_ticket(
            str(guild.id),
            str(ticket_channel.id),
            str(interaction.user.id),
            "Support"  # Default type
        )
        
        # Send welcome message
        welcome_view = create_ticket_welcome_view()
        await ticket_channel.send(
            f"👋 Hello {interaction.user.mention}! Support staff will be with you shortly.\n"
            f"Please describe your issue in detail.",
            view=welcome_view
        )
        
        await interaction.followup.send(
            f"✅ Ticket created! {ticket_channel.mention}",
            ephemeral=True
        )
        
        logger.info(f"Created ticket {ticket_channel.name} for {interaction.user} in {guild.name}")

    async def handle_role_action(self, interaction: discord.Interaction, component_id: str):
        """Handle role assignment button."""
        await interaction.response.send_message(
            "✅ Role action triggered! (Not yet implemented)",
            ephemeral=True
        )

    async def handle_select_menu(self, interaction: discord.Interaction):
        """Handle select menu interaction."""
        selected_values = interaction.data.get("values", [])
        await interaction.response.send_message(
            f"✅ Selected: {', '.join(selected_values)}",
            ephemeral=True
        )

    async def handle_custom_action(self, interaction: discord.Interaction, component_id: str):
        """Handle custom action button."""
        await interaction.response.send_message(
            f"✅ Custom action triggered!",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(DashboardInteractions(bot))
