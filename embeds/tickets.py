"""
embeds/tickets.py
Components V2 views and embeds for Miso Bot's Ticket System.
"""

from datetime import datetime, timezone
import discord
from discord.ui import LayoutView, Container, TextDisplay, Separator, ActionRow

import config

TICKET_TYPES = {
    "support": {
        "label": "Support",
        "desc": "Need help or have general server questions",
        "emoji": config.EMOJI_TICKET_PURPLE,
        "prefix": "ticket",
    },
    "report": {
        "label": "Report",
        "desc": "Report a rule breaker or server issue",
        "emoji": config.EMOJI_REPORT_PURPLE,
        "prefix": "report",
    },
    "staff_apply": {
        "label": "Staff Application",
        "desc": "Apply to join the server staff team",
        "emoji": config.EMOJI_APPLICATION_PURPLE,
        "prefix": "apply",
    },
}


# ==========================================
# TICKET PANEL COMPONENTS V2 VIEW
# ==========================================

class TicketPanelSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Support",
                description="Need help or have general server questions",
                emoji=discord.PartialEmoji.from_str(config.EMOJI_TICKET_PURPLE),
                value="support",
            ),
            discord.SelectOption(
                label="Report",
                description="Report a rule breaker or server issue",
                emoji=discord.PartialEmoji.from_str(config.EMOJI_REPORT_PURPLE),
                value="report",
            ),
            discord.SelectOption(
                label="Staff Application",
                description="Apply to join the server staff team",
                emoji=discord.PartialEmoji.from_str(config.EMOJI_APPLICATION_PURPLE),
                value="staff_apply",
            ),
        ]
        super().__init__(
            placeholder="Select a ticket category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="miso_ticket_create_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Tickets")
        if cog:
            await cog.handle_ticket_creation(interaction, self.values[0])


def create_ticket_panel_view() -> LayoutView:
    """Generates the Components V2 Ticket Panel message view."""
    panel_text = (
        f"## {config.EMOJI_TICKET} Support\n"
        f"Here you can talk to support, report an issue, or apply for staff.\n"
        f"Select a category from the dropdown below to create a ticket."
    )

    container = Container(
        TextDisplay(panel_text),
        Separator(),
        ActionRow(TicketPanelSelect()),
        accent_color=discord.Color.from_rgb(162, 64, 247),
    )

    view = LayoutView()
    view.add_item(container)
    return view


# ==========================================
# INSIDE TICKET CONTROLS (COMPONENTS V2)
# ==========================================

class CloseTicketButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Close Ticket",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id="miso_ticket_close_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Tickets")
        if cog:
            await cog.prompt_close_ticket(interaction)


class ClaimTicketButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Claim Ticket",
            style=discord.ButtonStyle.secondary,
            emoji="📋",
            custom_id="miso_ticket_claim_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Tickets")
        if cog:
            await cog.handle_claim_ticket(interaction)


def create_ticket_welcome_view(
    user: discord.User | discord.Member,
    ticket_type: str,
    ticket_num: int,
) -> LayoutView:
    """Generates the Components V2 welcome container inside the newly opened ticket channel."""
    info = TICKET_TYPES.get(ticket_type, TICKET_TYPES["support"])
    type_emoji = info["emoji"]
    type_label = info["label"]

    welcome_text = (
        f"### {type_emoji} {type_label} Ticket `#{ticket_num:04d}`\n"
        f"Welcome {user.mention}! Support staff will assist you shortly.\n"
        f"Please state your issue or questions with as much detail as possible.\n\u200b"
    )

    container = Container(
        TextDisplay(welcome_text),
        Separator(),
        ActionRow(CloseTicketButton(), ClaimTicketButton()),
        accent_color=discord.Color.from_rgb(162, 64, 247),
    )

    view = LayoutView()
    view.add_item(container)
    return view
