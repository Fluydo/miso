# -*- coding: utf-8 -*-
"""
cogs/custom_commands.py
Custom command system - create server-specific commands with custom responses.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional

logger = logging.getLogger("miso.cogs.custom_commands")


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    custom_group = app_commands.Group(name="custom", description="Manage custom commands")

    @custom_group.command(name="create", description="Create a new custom command (Admin only)")
    @app_commands.describe(
        trigger="Command name (e.g., 'rules' for /rules)",
        response="Simple text response (optional if using embed)",
        embed_title="Embed title (optional)",
        embed_description="Embed description (optional)",
        embed_color="Embed color as hex (e.g., 0x5865F2) (optional)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def custom_create(
        self,
        interaction: discord.Interaction,
        trigger: str,
        response: str = None,
        embed_title: str = None,
        embed_description: str = None,
        embed_color: str = None
    ) -> None:
        """Create a custom command."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.custom_commands import create_custom_command

        # Parse color
        color_int = None
        if embed_color:
            try:
                color_int = int(embed_color.replace('0x', '').replace('#', ''), 16)
            except ValueError:
                await interaction.followup.send("❌ Invalid color format! Use hex format like `0x5865F2` or `#5865F2`", ephemeral=True)
                return

        result = await create_custom_command(
            guild_id=interaction.guild.id,
            trigger=trigger.lower(),
            created_by=interaction.user.id,
            response_text=response,
            embed_title=embed_title,
            embed_description=embed_description,
            embed_color=color_int
        )

        if result['success']:
            await interaction.followup.send(
                f"✅ {result['message']}\n\n**Note:** The command will be available as `/cc {trigger}` after you restart the bot or it auto-syncs.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)

    @custom_group.command(name="delete", description="Delete a custom command (Admin only)")
    @app_commands.describe(trigger="Command name to delete")
    @app_commands.checks.has_permissions(administrator=True)
    async def custom_delete(self, interaction: discord.Interaction, trigger: str) -> None:
        """Delete a custom command."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.custom_commands import delete_custom_command

        success = await delete_custom_command(interaction.guild.id, trigger.lower())

        if success:
            await interaction.followup.send(
                f"✅ Custom command `{trigger}` has been deleted!\n\n**Note:** The command will be removed after bot restart or auto-sync.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ Command `{trigger}` not found!", ephemeral=True)

    @custom_group.command(name="list", description="List all custom commands")
    async def custom_list(self, interaction: discord.Interaction) -> None:
        """List all custom commands for this server."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        from functions.custom_commands import get_all_custom_commands

        commands = await get_all_custom_commands(interaction.guild.id)

        if not commands:
            await interaction.followup.send("📝 This server has no custom commands yet!\n\nAdmins can create them with `/custom create`")
            return

        embed = discord.Embed(
            title=f"📝 Custom Commands for {interaction.guild.name}",
            description=f"Use `/cc <command>` to run them",
            color=discord.Color.blue()
        )

        # Group commands (max 25 fields)
        for cmd in commands[:25]:
            response_preview = ""
            if cmd.get('response_text'):
                preview_text = cmd['response_text'][:50]
                response_preview = f"Text: {preview_text}{'...' if len(cmd['response_text']) > 50 else ''}"
            elif cmd.get('embed_title'):
                response_preview = f"Embed: {cmd['embed_title']}"
            else:
                response_preview = "Custom embed"

            embed.add_field(
                name=f"/{cmd['trigger']}",
                value=response_preview,
                inline=True
            )

        if len(commands) > 25:
            embed.set_footer(text=f"Showing 25 of {len(commands)} commands")
        else:
            embed.set_footer(text=f"{len(commands)} custom command{'s' if len(commands) != 1 else ''}")

        await interaction.followup.send(embed=embed)

    # Dynamic command handler - /cc <trigger>
    cc_group = app_commands.Group(name="cc", description="Run custom commands")

    @cc_group.command(name="run", description="Run a custom command")
    @app_commands.describe(command="The custom command to run")
    async def cc_run(self, interaction: discord.Interaction, command: str) -> None:
        """Run a custom command."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        from functions.custom_commands import get_custom_command

        cmd = await get_custom_command(interaction.guild.id, command.lower())

        if not cmd:
            await interaction.followup.send(
                f"❌ Custom command `{command}` not found!\n\nUse `/custom list` to see available commands.",
                ephemeral=True
            )
            return

        # Build response
        content = cmd.get('response_text')
        embed = None

        if cmd.get('embed_title') or cmd.get('embed_description'):
            embed = discord.Embed(
                title=cmd.get('embed_title'),
                description=cmd.get('embed_description'),
                color=discord.Color(cmd['embed_color']) if cmd.get('embed_color') else discord.Color.blue()
            )
            if cmd.get('embed_image_url'):
                embed.set_image(url=cmd['embed_image_url'])

        await interaction.followup.send(content=content, embed=embed)


async def setup(bot: commands.Bot) -> None:
    cog = CustomCommands(bot)
    await bot.add_cog(cog)
    # Command groups are auto-registered by the cog, no need to manually add them
