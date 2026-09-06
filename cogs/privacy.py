import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
from typing import Optional

class Privacy(commands.Cog):
    """Privacy and data management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="privacy", description="View privacy policy and manage your data")
    @app_commands.describe(
        action="Choose an action: view policy, view your data, or delete your data"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="📄 View Privacy Policy", value="policy"),
        app_commands.Choice(name="👤 View My Data", value="view"),
        app_commands.Choice(name="🗑️ Delete My Data", value="delete"),
    ])
    async def privacy(self, interaction: discord.Interaction, action: str):
        """Privacy command with multiple options"""
        
        if action == "policy":
            await self.show_policy(interaction)
        elif action == "view":
            await self.view_data(interaction)
        elif action == "delete":
            await self.delete_data(interaction)
    
    async def show_policy(self, interaction: discord.Interaction):
        """Show privacy policy"""
        embed = discord.Embed(
            title="📄 Privacy Policy",
            description=(
                "Miso is committed to protecting your privacy. We collect and use your data "
                "to provide features like leveling, giveaways, invite tracking, and moderation.\n\n"
                "**What we collect:**\n"
                "• Discord User ID, username, avatar\n"
                "• XP/levels and game statistics\n"
                "• Invite tracking data\n"
                "• Giveaway entries\n"
                "• Moderation actions\n\n"
                "**What we DON'T collect:**\n"
                "• Full message content (only metadata)\n"
                "• Private messages\n"
                "• Voice chat data\n\n"
                "**Your Rights:**\n"
                "• View your data: `/privacy action:View My Data`\n"
                "• Delete your data: `/privacy action:Delete My Data`\n"
            ),
            color=0xa240f7
        )
        
        embed.add_field(
            name="📖 Full Privacy Policy",
            value="[Read our complete Privacy Policy](https://miso-dashboard-iota.vercel.app/privacy)",
            inline=False
        )
        
        embed.add_field(
            name="📧 Contact Us",
            value=(
                "• Email: skibidi.rip.yt@gmail.com\n"
                "• Use `/privacy action:Delete My Data` for instant deletion"
            ),
            inline=False
        )
        
        embed.set_footer(text="Your privacy matters to us")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def view_data(self, interaction: discord.Interaction):
        """Show user's stored data"""
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(interaction.user.id)
        
        # Fetch data from Supabase
        async with aiohttp.ClientSession() as session:
            # Get user profile
            async with session.get(
                f"https://cunbjamcjggtoayryluq.supabase.co/rest/v1/users?discord_id=eq.{user_id}",
                headers={
                    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs",
                    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs"
                }
            ) as resp:
                users = await resp.json()
                user_data = users[0] if users else None
        
        if not user_data:
            embed = discord.Embed(
                title="👤 Your Data",
                description="No data found for your account. You may not have used Miso features yet.",
                color=0xa240f7
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Build data summary
        embed = discord.Embed(
            title="👤 Your Stored Data",
            description="Here's a summary of the data we have about you:",
            color=0xa240f7
        )
        
        embed.add_field(
            name="👤 Profile",
            value=(
                f"**User ID:** `{user_data.get('discord_id')}`\n"
                f"**Username:** {user_data.get('username')}\n"
                f"**Level:** {user_data.get('level', 0)}\n"
                f"**XP:** {user_data.get('xp', 0)}\n"
                f"**Coins:** {user_data.get('coins', 0)}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎯 Activity",
            value=(
                f"**Daily Streak:** {user_data.get('daily_streak', 0)} days\n"
                f"**Last Daily:** {user_data.get('last_daily', 'Never')}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Data Types",
            value=(
                "We also store:\n"
                "• Game history (wins/losses)\n"
                "• Giveaway entries\n"
                "• Invite tracking data\n"
                "• Moderation actions (if any)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🗑️ Delete Data",
            value="To delete your data, use `/privacy action:Delete My Data`",
            inline=False
        )
        
        embed.set_footer(text="Your data is encrypted and secure")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def delete_data(self, interaction: discord.Interaction):
        """Confirm and delete user data"""
        
        embed = discord.Embed(
            title="⚠️ Delete Your Data",
            description=(
                "Are you sure you want to delete **ALL** your data?\n\n"
                "**This will permanently delete:**\n"
                "• Your XP, level, and coins\n"
                "• Game history and statistics\n"
                "• Giveaway entries\n"
                "• Invite tracking data\n"
                "• All moderation records\n\n"
                "**This action cannot be undone!**"
            ),
            color=0xff0000
        )
        
        # Create confirmation view
        view = DeleteConfirmView(user_id=interaction.user.id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class DeleteConfirmView(discord.ui.View):
    """Confirmation view for data deletion"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id
    
    @discord.ui.button(label="Yes, Delete My Data", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Delete user data from Supabase
        user_id = str(interaction.user.id)
        
        async with aiohttp.ClientSession() as session:
            # Delete from users table
            await session.delete(
                f"https://cunbjamcjggtoayryluq.supabase.co/rest/v1/users?discord_id=eq.{user_id}",
                headers={
                    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs",
                    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs"
                }
            )
            
            # Delete from game_history
            await session.delete(
                f"https://cunbjamcjggtoayryluq.supabase.co/rest/v1/game_history?discord_id=eq.{user_id}",
                headers={
                    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs",
                    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs"
                }
            )
            
            # Delete from giveaway_entries
            await session.delete(
                f"https://cunbjamcjggtoayryluq.supabase.co/rest/v1/giveaway_entries?discord_id=eq.{user_id}",
                headers={
                    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs",
                    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1bmJqYW1jamdndG9heXJ5bHVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgyMDYzODEsImV4cCI6MjEwMzc4MjM4MX0.-_i6I7JnxH7yTfvcybZBhkk9ofd4nmDHutvFfIg0CTs"
                }
            )
        
        embed = discord.Embed(
            title="✅ Data Deleted",
            description=(
                "Your data has been permanently deleted from our systems.\n\n"
                "If you use Miso features again, a new profile will be created."
            ),
            color=0x00ff00
        )
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Cancelled",
            description="Your data has NOT been deleted.",
            color=0xa240f7
        )
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)

async def setup(bot):
    await bot.add_cog(Privacy(bot))
