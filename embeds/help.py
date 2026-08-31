"""
embeds/help.py
Help menu embeds and Select-based navigation view for Miso Bot.
"""

from datetime import datetime, timezone
import discord
import config


# ==========================================
# PER-CATEGORY EMBED BUILDERS
# ==========================================

def _base_help_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"{config.BOT_NAME} • Use / to autocomplete commands")
    return embed


def help_overview_embed(bot: discord.Client) -> discord.Embed:
    embed = discord.Embed(
        color=config.COLOR_PRIMARY,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{config.BOT_NAME} — Command Reference",
        icon_url=bot.user.display_avatar.url if bot.user else None,
    )
    embed.description = (
        f"Hi! I'm **{config.BOT_NAME}**, a moderation, utility & minigames bot.\n"
        f"Use the dropdown below to browse commands by category.\n\u200b"
    )

    embed.add_field(
        name=f"`🔨` **Moderation**",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} "
            f"`ban` `tempban` `unban` `kick` `timeout` `untimeout` "
            f"`warn` `warnings` `clearwarnings` `clear`"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"`🎮` **Games & Economy**",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} "
            f"`mines` `coinflip` `slots` `daily` `balance` `pay` `richest`"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"`🎫` **Tickets**",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} "
            f"`ticket panel` `ticket add` `ticket remove` `ticket close` `ticket category`"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"`⚙️` **Configuration**",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} "
            f"`setmodlog` `disablemodlog` `modlogstatus`"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"`🔗` **Invites**",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} "
            f"`invites stats` `invites leaderboard` `invites reset`"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"`🛠️` **Utility**",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} "
            f"`ping` `avatar` `userinfo` `serverinfo` `botinfo` `help`"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"`👁️` **Status**",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} "
            f"`userstatus`"
        ),
        inline=False,
    )
    embed.set_footer(text=f"{config.BOT_NAME} • Select a category below for details")
    return embed


def help_moderation_embed() -> discord.Embed:
    embed = _base_help_embed(
        f"`🔨` Moderation Commands",
        "Commands for managing members and keeping the server safe.\n"
        "🔒 = Requires specific permission.\n\u200b",
    )
    fields = [
        ("`/ban` `@user` `[reason]`", f"{config.EMOJI_CHEVRON_RIGHT} Permanently ban a member. 🔒 Ban Members"),
        ("`/tempban` `@user` `duration` `[reason]`", f"{config.EMOJI_CHEVRON_RIGHT} Temporarily ban a member. 🔒 Ban Members"),
        ("`/unban` `user_id` `[reason]`", f"{config.EMOJI_CHEVRON_RIGHT} Unban a user by their Discord ID. 🔒 Ban Members"),
        ("`/kick` `@user` `[reason]`", f"{config.EMOJI_CHEVRON_RIGHT} Kick a member from the server. 🔒 Kick Members"),
        ("`/timeout` `@user` `duration` `[reason]`", f"{config.EMOJI_CHEVRON_RIGHT} Mute a member (max 28d). 🔒 Moderate Members"),
        ("`/untimeout` `@user` `[reason]`", f"{config.EMOJI_CHEVRON_RIGHT} Remove an active timeout. 🔒 Moderate Members"),
        ("`/warn` `@user` `[reason]`", f"{config.EMOJI_CHEVRON_RIGHT} Issue a formal warning. 🔒 Manage Messages"),
        ("`/warnings` `@user`", f"{config.EMOJI_CHEVRON_RIGHT} View all warnings for a member. 🔒 Manage Messages"),
        ("`/clearwarnings` `@user`", f"{config.EMOJI_CHEVRON_RIGHT} Clear all warnings for a member. 🔒 Manage Messages"),
        ("`/clear` `amount`", f"{config.EMOJI_CHEVRON_RIGHT} Bulk delete 1–100 messages. 🔒 Manage Messages"),
    ]
    for name, value in fields:
        embed.add_field(name=name, value=value, inline=False)
    return embed


def help_games_embed() -> discord.Embed:
    embed = _base_help_embed(
        f"`🎮` Minigames & Economy",
        f"Earn coins {config.EMOJI_COIN} and play interactive visual games!\n\u200b",
    )
    fields = [
        ("`/mines` `[bet]` `[bombs]` `[grid]`", f"{config.EMOJI_CHEVRON_RIGHT} Interactive Mines (3x3, 4x4, or 5x5)! Click custom emoji tiles to reveal gems and cash out."),
        ("`/blackjack` `[bet]`", f"{config.EMOJI_CHEVRON_RIGHT} Interactive visual Blackjack (21)! Hit, Stand, or Double Down against the dealer."),
        ("`/slots` `[bet]`", f"{config.EMOJI_CHEVRON_RIGHT} Spin the 3-segment visual slot machine for up to 10x jackpot."),
        ("`/coinflip` `bet` `choice`", f"{config.EMOJI_CHEVRON_RIGHT} 50/50 coin flip against the house for 2.0x payout."),
        ("`/daily`", f"{config.EMOJI_CHEVRON_RIGHT} Claim free daily coins and build your consecutive day streak!"),
        ("`/balance` `[@user]`", f"{config.EMOJI_CHEVRON_RIGHT} View your or another user's current coin balance."),
        ("`/pay` `@user` `amount`", f"{config.EMOJI_CHEVRON_RIGHT} Transfer coins to another server member."),
        ("`/richest`", f"{config.EMOJI_CHEVRON_RIGHT} View the visual paginated economy leaderboard."),
    ]
    for name, value in fields:
        embed.add_field(name=name, value=value, inline=False)
    return embed


def help_tickets_embed() -> discord.Embed:
    embed = _base_help_embed(
        f"`🎫` Ticket System Commands",
        "Commands for setting up and managing support and application tickets.\n\u200b",
    )
    fields = [
        (
            "`/ticket panel` `[#channel]`",
            f"{config.EMOJI_CHEVRON_RIGHT} Send the Components V2 ticket creation panel with Support, Report, and Staff Application options. 🔒 Manage Server",
        ),
        (
            "`/ticket category` `#category`",
            f"{config.EMOJI_CHEVRON_RIGHT} Set the category where new tickets are created. 🔒 Manage Server",
        ),
        (
            "`/ticket add` `@user`",
            f"{config.EMOJI_CHEVRON_RIGHT} Add a member to the current ticket channel. 🔒 Manage Messages",
        ),
        (
            "`/ticket remove` `@user`",
            f"{config.EMOJI_CHEVRON_RIGHT} Remove a member from the current ticket channel. 🔒 Manage Messages",
        ),
        (
            "`/ticket close` `[reason]`",
            f"{config.EMOJI_CHEVRON_RIGHT} Close the ticket with transcript and audit logging.",
        ),
    ]
    for name, value in fields:
        embed.add_field(name=name, value=value, inline=False)
    return embed


def help_config_embed() -> discord.Embed:
    embed = _base_help_embed(
        f"`⚙️` Configuration Commands",
        "Commands for configuring Miso's behaviour in your server.\n\u200b",
    )
    fields = [
        (
            "`/setmodlog` `#channel`",
            f"{config.EMOJI_CHEVRON_RIGHT} Set the channel for moderation & audit logs.\n"
            f"{config.EMOJI_CHEVRON_RIGHT} Supports **Text Channels** and **Forum Channels**. 🔒 Manage Server",
        ),
        (
            "`/disablemodlog`",
            f"{config.EMOJI_CHEVRON_RIGHT} Disable moderation logging for this server. 🔒 Manage Server",
        ),
        (
            "`/modlogstatus`",
            f"{config.EMOJI_CHEVRON_RIGHT} Check the currently configured mod log channel. 🔒 Manage Messages",
        ),
    ]
    for name, value in fields:
        embed.add_field(name=name, value=value, inline=False)
    embed.add_field(
        name=f"{config.EMOJI_INFO} Forum Channel Logging",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} Setting a **Forum Channel** auto-creates 5 organized threads:\n"
            f"`🔨・moderation` `💬・messages` `👥・members` `🏷️・profiles` `📁・server events`"
        ),
        inline=False,
    )
    return embed


def help_invites_embed() -> discord.Embed:
    embed = _base_help_embed(
        f"`🔗` Invite Commands",
        "Track who invited who and view invite leaderboards.\n\u200b",
    )
    fields = [
        (
            "`/invites stats` `[@user]`",
            f"{config.EMOJI_CHEVRON_RIGHT} View invite stats for yourself or another user.\n"
            f"{config.EMOJI_CHEVRON_RIGHT} Shows total, active, and left counts.",
        ),
        (
            "`/invites leaderboard`",
            f"{config.EMOJI_CHEVRON_RIGHT} Top 10 inviters sorted by active invite count.",
        ),
        (
            "`/invites reset` `@user`",
            f"{config.EMOJI_CHEVRON_RIGHT} Clear all invite attribution for a user. 🔒 Manage Server",
        ),
    ]
    for name, value in fields:
        embed.add_field(name=name, value=value, inline=False)
    embed.add_field(
        name=f"{config.EMOJI_INFO} How Tracking Works",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} Miso compares invite usage counts on each join.\n"
            f"{config.EMOJI_CHEVRON_RIGHT} Data persists across restarts.\n"
            f"{config.EMOJI_CHEVRON_RIGHT} Requires **Manage Server** permission to read invites."
        ),
        inline=False,
    )
    return embed


def help_utility_embed() -> discord.Embed:
    embed = _base_help_embed(
        f"`🛠️` Utility Commands",
        "General-purpose commands for server and user information.\n\u200b",
    )
    fields = [
        ("`/ping`", f"{config.EMOJI_CHEVRON_RIGHT} Check the bot's current gateway latency."),
        ("`/avatar` `[@user]`", f"{config.EMOJI_CHEVRON_RIGHT} View the full-size avatar of any user."),
        ("`/userinfo` `[@user]`", f"{config.EMOJI_CHEVRON_RIGHT} View profile info — roles, join date, permissions."),
        ("`/serverinfo`", f"{config.EMOJI_CHEVRON_RIGHT} View detailed server information (Components V2)."),
        ("`/botinfo`", f"{config.EMOJI_CHEVRON_RIGHT} View Miso's version, uptime, and system stats."),
        ("`/help`", f"{config.EMOJI_CHEVRON_RIGHT} Display this help menu."),
    ]
    for name, value in fields:
        embed.add_field(name=name, value=value, inline=False)
    return embed


def help_status_embed() -> discord.Embed:
    embed = _base_help_embed(
        f"`👁️` Status Commands",
        "View presence and activity information for members.\n\u200b",
    )
    embed.add_field(
        name="`/userstatus` `[@user]`",
        value=(
            f"{config.EMOJI_CHEVRON_RIGHT} Display a member's current online status, "
            f"custom status, and active activities."
        ),
        inline=False,
    )
    return embed


# ==========================================
# INTERACTIVE NAVIGATION VIEW
# ==========================================

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label="Overview", description="All command categories at a glance", emoji="🏠", value="overview", default=True),
            discord.SelectOption(label="Moderation", description="ban, kick, timeout, warn, clear", emoji="🔨", value="moderation"),
            discord.SelectOption(label="Games & Economy", description="mines, coinflip, slots, daily, balance", emoji="🎮", value="games"),
            discord.SelectOption(label="Tickets", description="Support, report, and staff application panel", emoji="🎫", value="tickets"),
            discord.SelectOption(label="Configuration", description="Mod log setup", emoji="⚙️", value="config"),
            discord.SelectOption(label="Invites", description="Invite tracking and leaderboard", emoji="🔗", value="invites"),
            discord.SelectOption(label="Utility", description="Server info, user info, ping", emoji="🛠️", value="utility"),
            discord.SelectOption(label="Status", description="User presence and activities", emoji="👁️", value="status"),
        ]
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        value = self.values[0]

        for option in self.options:
            option.default = option.value == value

        embed_map = {
            "overview": help_overview_embed(self.bot),
            "moderation": help_moderation_embed(),
            "games": help_games_embed(),
            "tickets": help_tickets_embed(),
            "config": help_config_embed(),
            "invites": help_invites_embed(),
            "utility": help_utility_embed(),
            "status": help_status_embed(),
        }
        embed = embed_map.get(value, help_overview_embed(self.bot))
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, bot: discord.Client) -> None:
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot))
