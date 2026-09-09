# -*- coding: utf-8 -*-
"""
cogs/polls.py
Interactive poll system with button voting.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("miso.cogs.polls")


class PollView(discord.ui.View):
    """Interactive poll view with voting buttons."""
    
    def __init__(self, poll_data: dict):
        super().__init__(timeout=None)  # Persistent view
        self.poll_data = poll_data
        
        # Add button for each option (max 10)
        for option in poll_data['options'][:10]:
            button = discord.ui.Button(
                label=option['text'][:80],  # Discord button label limit
                custom_id=f"poll_{poll_data['id']}_{option['id']}",
                style=discord.ButtonStyle.primary
            )
            button.callback = self.create_vote_callback(option['id'])
            self.add_item(button)
    
    def create_vote_callback(self, option_id: int):
        async def vote_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            from functions.polls import vote_poll, get_poll
            
            result = await vote_poll(int(self.poll_data['message_id']), interaction.user.id, option_id)
            
            if result['success']:
                # Update the poll message
                updated_poll = await get_poll(int(self.poll_data['message_id']))
                if updated_poll:
                    embed = create_poll_embed(updated_poll)
                    try:
                        await interaction.message.edit(embed=embed)
                    except:
                        pass
                
                await interaction.followup.send("✅ Your vote has been recorded!", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)
        
        return vote_callback


def create_poll_embed(poll: dict) -> discord.Embed:
    """Create an embed for a poll with vote counts."""
    embed = discord.Embed(
        title=f"📊 {poll['question']}",
        color=discord.Color.blue() if poll['is_active'] else discord.Color.gray()
    )
    
    # Calculate total votes
    total_votes = sum(len(opt['votes']) for opt in poll['options'])
    
    # Add each option with progress bar
    for option in poll['options']:
        vote_count = len(option['votes'])
        percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
        
        # Create a simple text progress bar
        bar_length = 10
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        embed.add_field(
            name=f"{option['text']}",
            value=f"{bar} {vote_count} votes ({percentage:.1f}%)",
            inline=False
        )
    
    # Footer info
    footer_text = f"Total votes: {total_votes}"
    if poll.get('ends_at'):
        ends_at = datetime.fromisoformat(poll['ends_at'])
        time_left = ends_at - datetime.utcnow()
        if time_left.total_seconds() > 0:
            hours = int(time_left.total_seconds() // 3600)
            footer_text += f" • Ends in {hours}h"
        else:
            footer_text += " • Ended"
    
    if not poll['is_active']:
        footer_text += " • Poll Closed"
    
    embed.set_footer(text=footer_text)
    
    return embed


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="poll", description="Create an interactive poll")
    @app_commands.describe(
        question="The poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)",
        duration="Duration in hours (optional, leave empty for no time limit)"
    )
    async def create_poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: Optional[str] = None,
        option4: Optional[str] = None,
        option5: Optional[str] = None,
        duration: Optional[int] = None
    ) -> None:
        """Create a new poll."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        # Collect options
        options = [option1, option2]
        for opt in [option3, option4, option5]:
            if opt:
                options.append(opt)

        # Create placeholder message first
        embed = discord.Embed(
            title=f"📊 {question}",
            description="Setting up poll...",
            color=discord.Color.blue()
        )
        message = await interaction.followup.send(embed=embed, wait=True)

        # Save poll to database
        from functions.polls import create_poll

        result = await create_poll(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=message.id,
            question=question,
            options=options,
            created_by=interaction.user.id,
            duration_hours=duration,
            allow_multiple=False
        )

        if not result['success']:
            await message.edit(content=f"❌ {result['message']}", embed=None)
            return

        # Get the poll data and create view
        from functions.polls import get_poll
        poll_data = await get_poll(message.id)
        
        if not poll_data:
            await message.edit(content="❌ Failed to create poll!", embed=None)
            return

        # Update message with proper embed and buttons
        embed = create_poll_embed(poll_data)
        view = PollView(poll_data)
        
        await message.edit(embed=embed, view=view)

    @app_commands.command(name="endpoll", description="End a poll early (Admin or poll creator only)")
    @app_commands.describe(message_id="The message ID of the poll to end")
    async def end_poll(self, interaction: discord.Interaction, message_id: str) -> None:
        """End a poll."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from functions.polls import get_poll, end_poll

        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.followup.send("❌ Invalid message ID!", ephemeral=True)
            return

        poll = await get_poll(msg_id)
        
        if not poll:
            await interaction.followup.send("❌ Poll not found!", ephemeral=True)
            return

        # Check permissions
        is_creator = int(poll['created_by']) == interaction.user.id
        is_admin = interaction.user.guild_permissions.administrator
        
        if not is_creator and not is_admin:
            await interaction.followup.send("❌ Only the poll creator or admins can end this poll!", ephemeral=True)
            return

        success = await end_poll(msg_id)

        if success:
            # Update the message
            embed = create_poll_embed(poll)
            try:
                channel = interaction.guild.get_channel(int(poll['channel_id']))
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(embed=embed, view=None)  # Remove buttons
            except:
                pass

            await interaction.followup.send("✅ Poll has been ended!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to end poll!", ephemeral=True)

    @app_commands.command(name="polls", description="List active polls in this server")
    async def list_polls(self, interaction: discord.Interaction) -> None:
        """List active polls."""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer()

        from functions.polls import get_active_polls

        polls = await get_active_polls(interaction.guild.id)

        if not polls:
            await interaction.followup.send("📊 There are no active polls in this server right now!")
            return

        embed = discord.Embed(
            title=f"📊 Active Polls in {interaction.guild.name}",
            color=discord.Color.blue()
        )

        for poll in polls[:10]:  # Show max 10
            total_votes = sum(len(opt['votes']) for opt in poll['options'])
            
            channel = interaction.guild.get_channel(int(poll['channel_id']))
            channel_mention = channel.mention if channel else f"Channel {poll['channel_id']}"
            
            value = f"{channel_mention}\n"
            value += f"Votes: {total_votes}\n"
            value += f"[Jump to Poll](https://discord.com/channels/{poll['guild_id']}/{poll['channel_id']}/{poll['message_id']})"
            
            embed.add_field(
                name=poll['question'][:100],
                value=value,
                inline=False
            )

        embed.set_footer(text=f"{len(polls)} active poll{'s' if len(polls) != 1 else ''}")

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
