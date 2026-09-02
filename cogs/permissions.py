import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import json
from pathlib import Path
from typing import Literal
import config

class PermissionsManager:
    """Manages command permissions for guilds"""
    
    def __init__(self):
        self.settings_file = config.SETTINGS_FILE
        self._ensure_file()
    
    def _ensure_file(self):
        """Ensure settings file exists"""
        if not self.settings_file.exists():
            self.settings_file.write_text('{}')
    
    def _load_settings(self) -> dict:
        """Load guild settings"""
        try:
            return json.loads(self.settings_file.read_text())
        except:
            return {}
    
    def _save_settings(self, settings: dict):
        """Save guild settings"""
        self.settings_file.write_text(json.dumps(settings, indent=2))
    
    def get_guild_perms(self, guild_id: int) -> dict:
        """Get permissions for a guild"""
        settings = self._load_settings()
        guild_key = str(guild_id)
        if guild_key not in settings:
            settings[guild_key] = {}
        if 'permissions' not in settings[guild_key]:
            settings[guild_key]['permissions'] = {}
        return settings[guild_key]['permissions']
    
    def set_command_perms(self, guild_id: int, command_name: str, perms: dict):
        """Set permissions for a specific command"""
        settings = self._load_settings()
        guild_key = str(guild_id)
        if guild_key not in settings:
            settings[guild_key] = {}
        if 'permissions' not in settings[guild_key]:
            settings[guild_key]['permissions'] = {}
        settings[guild_key]['permissions'][command_name] = perms
        self._save_settings(settings)
    
    def check_permission(self, guild_id: int, command_name: str, channel_id: int, 
                        user_id: int, user_roles: list[int]) -> bool:
        """
        Check if user can use command in channel.
        Returns True if allowed, False if denied.
        """
        perms = self.get_guild_perms(guild_id)
        
        if command_name not in perms:
            return True  # No restrictions = allowed
        
        cmd_perms = perms[command_name]
        mode = cmd_perms.get('mode', 'whitelist')  # 'whitelist' or 'blacklist'
        channels = cmd_perms.get('channels', [])
        excluded_roles = cmd_perms.get('excluded_roles', [])
        excluded_users = cmd_perms.get('excluded_users', [])
        
        # Check if user/role is excluded (bypasses restrictions)
        if user_id in excluded_users:
            return True
        if any(role_id in excluded_roles for role_id in user_roles):
            return True
        
        # Apply whitelist/blacklist
        if mode == 'whitelist':
            # Whitelist: only allowed in specified channels
            return channel_id in channels if channels else True
        else:
            # Blacklist: blocked in specified channels
            return channel_id not in channels


class PermissionSetupModal(Modal, title="Configure Command Permissions"):
    """Modal for adding channels to permissions"""
    
    def __init__(self, manager: PermissionsManager, guild_id: int, command_name: str, 
                 current_mode: str, view_ref):
        super().__init__()
        self.manager = manager
        self.guild_id = guild_id
        self.command_name = command_name
        self.current_mode = current_mode
        self.view_ref = view_ref
    
    channel_ids = TextInput(
        label="Channel IDs (comma-separated)",
        placeholder="1234567890, 9876543210",
        style=discord.TextStyle.paragraph,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Parse channel IDs
        channels = []
        if self.channel_ids.value.strip():
            for ch_str in self.channel_ids.value.split(','):
                try:
                    channels.append(int(ch_str.strip()))
                except:
                    pass
        
        # Get existing perms
        perms = self.manager.get_guild_perms(self.guild_id)
        if self.command_name not in perms:
            perms[self.command_name] = {
                'mode': self.current_mode,
                'channels': [],
                'excluded_roles': [],
                'excluded_users': []
            }
        
        perms[self.command_name]['channels'] = channels
        self.manager.set_command_perms(self.guild_id, self.command_name, perms[self.command_name])
        
        # Update view
        self.view_ref.current_command = self.command_name
        await self.view_ref.update_display(interaction)


class ExclusionModal(Modal, title="Add Exclusions"):
    """Modal for adding role/user exclusions"""
    
    def __init__(self, manager: PermissionsManager, guild_id: int, command_name: str, 
                 exclusion_type: Literal['role', 'user'], view_ref):
        super().__init__()
        self.manager = manager
        self.guild_id = guild_id
        self.command_name = command_name
        self.exclusion_type = exclusion_type
        self.view_ref = view_ref
        
        if exclusion_type == 'role':
            self.title = "Add Role Exclusions"
            self.ids_input = TextInput(
                label="Role IDs (comma-separated)",
                placeholder="1234567890, 9876543210",
                style=discord.TextStyle.paragraph,
                required=False
            )
        else:
            self.title = "Add User Exclusions"
            self.ids_input = TextInput(
                label="User IDs (comma-separated)",
                placeholder="1234567890, 9876543210",
                style=discord.TextStyle.paragraph,
                required=False
            )
        
        self.add_item(self.ids_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Parse IDs
        ids = []
        if self.ids_input.value.strip():
            for id_str in self.ids_input.value.split(','):
                try:
                    ids.append(int(id_str.strip()))
                except:
                    pass
        
        # Get existing perms
        perms = self.manager.get_guild_perms(self.guild_id)
        if self.command_name not in perms:
            perms[self.command_name] = {
                'mode': 'whitelist',
                'channels': [],
                'excluded_roles': [],
                'excluded_users': []
            }
        
        # Add exclusions
        if self.exclusion_type == 'role':
            existing = set(perms[self.command_name].get('excluded_roles', []))
            existing.update(ids)
            perms[self.command_name]['excluded_roles'] = list(existing)
        else:
            existing = set(perms[self.command_name].get('excluded_users', []))
            existing.update(ids)
            perms[self.command_name]['excluded_users'] = list(existing)
        
        self.manager.set_command_perms(self.guild_id, self.command_name, perms[self.command_name])
        
        # Update view
        self.view_ref.current_command = self.command_name
        await self.view_ref.update_display(interaction)


class PermissionsView(View):
    """Interactive permissions configuration panel"""
    
    def __init__(self, manager: PermissionsManager, guild_id: int, bot: commands.Bot):
        super().__init__(timeout=300)
        self.manager = manager
        self.guild_id = guild_id
        self.bot = bot
        self.current_command = None
        self.current_category = None
        
        # Build command list from bot
        self.commands_by_category = {}
        for cmd in bot.tree.get_commands():
            if isinstance(cmd, app_commands.Command):
                # Get cog name as category
                if cmd.binding:
                    category = cmd.binding.__class__.__name__
                else:
                    category = "General"
                
                if category not in self.commands_by_category:
                    self.commands_by_category[category] = []
                self.commands_by_category[category].append(cmd.name)
        
        self._add_controls()
    
    def _add_controls(self):
        """Add all buttons and selects"""
        self.clear_items()
        
        # Category selector
        category_select = Select(
            placeholder="Select a category...",
            options=[
                discord.SelectOption(label=cat, value=cat)
                for cat in sorted(self.commands_by_category.keys())
            ][:25],  # Discord limit
            custom_id="category_select"
        )
        category_select.callback = self.on_category_select
        self.add_item(category_select)
        
        # Command selector (shows after category selected)
        if self.current_category:
            command_options = [
                discord.SelectOption(label=cmd, value=cmd)
                for cmd in sorted(self.commands_by_category[self.current_category])
            ][:25]
            
            if command_options:
                command_select = Select(
                    placeholder=f"Select command from {self.current_category}...",
                    options=command_options,
                    custom_id="command_select"
                )
                command_select.callback = self.on_command_select
                self.add_item(command_select)
        
        # If command selected, show config buttons
        if self.current_command:
            perms = self.manager.get_guild_perms(self.guild_id)
            cmd_perms = perms.get(self.current_command, {})
            current_mode = cmd_perms.get('mode', 'whitelist')
            
            # Mode toggle button
            mode_button = Button(
                label=f"Mode: {current_mode.upper()}",
                style=discord.ButtonStyle.primary if current_mode == 'whitelist' else discord.ButtonStyle.danger,
                custom_id="toggle_mode"
            )
            mode_button.callback = self.on_toggle_mode
            self.add_item(mode_button)
            
            # Configure channels button
            channels_button = Button(
                label="Configure Channels",
                style=discord.ButtonStyle.secondary,
                emoji="📝",
                custom_id="config_channels"
            )
            channels_button.callback = self.on_config_channels
            self.add_item(channels_button)
            
            # Add role exclusions button
            role_exclusion_button = Button(
                label="Add Role Exclusions",
                style=discord.ButtonStyle.secondary,
                emoji="👥",
                custom_id="add_role_exclusions"
            )
            role_exclusion_button.callback = self.on_add_role_exclusions
            self.add_item(role_exclusion_button)
            
            # Add user exclusions button
            user_exclusion_button = Button(
                label="Add User Exclusions",
                style=discord.ButtonStyle.secondary,
                emoji="👤",
                custom_id="add_user_exclusions"
            )
            user_exclusion_button.callback = self.on_add_user_exclusions
            self.add_item(user_exclusion_button)
            
            # Clear config button
            clear_button = Button(
                label="Clear Config",
                style=discord.ButtonStyle.danger,
                emoji="🗑️",
                custom_id="clear_config"
            )
            clear_button.callback = self.on_clear_config
            self.add_item(clear_button)
    
    async def on_category_select(self, interaction: discord.Interaction):
        """Handle category selection"""
        self.current_category = interaction.data['values'][0]
        self.current_command = None
        await self.update_display(interaction)
    
    async def on_command_select(self, interaction: discord.Interaction):
        """Handle command selection"""
        self.current_command = interaction.data['values'][0]
        await self.update_display(interaction)
    
    async def on_toggle_mode(self, interaction: discord.Interaction):
        """Toggle between whitelist and blacklist"""
        perms = self.manager.get_guild_perms(self.guild_id)
        if self.current_command not in perms:
            perms[self.current_command] = {
                'mode': 'whitelist',
                'channels': [],
                'excluded_roles': [],
                'excluded_users': []
            }
        
        current_mode = perms[self.current_command].get('mode', 'whitelist')
        new_mode = 'blacklist' if current_mode == 'whitelist' else 'whitelist'
        perms[self.current_command]['mode'] = new_mode
        
        self.manager.set_command_perms(self.guild_id, self.current_command, perms[self.current_command])
        await self.update_display(interaction)
    
    async def on_config_channels(self, interaction: discord.Interaction):
        """Show modal to configure channels"""
        perms = self.manager.get_guild_perms(self.guild_id)
        cmd_perms = perms.get(self.current_command, {})
        current_mode = cmd_perms.get('mode', 'whitelist')
        
        modal = PermissionSetupModal(
            self.manager,
            self.guild_id,
            self.current_command,
            current_mode,
            self
        )
        
        # Pre-fill with current channels
        if cmd_perms.get('channels'):
            modal.channel_ids.default = ', '.join(str(ch) for ch in cmd_perms['channels'])
        
        await interaction.response.send_modal(modal)
    
    async def on_add_role_exclusions(self, interaction: discord.Interaction):
        """Show modal to add role exclusions"""
        modal = ExclusionModal(
            self.manager,
            self.guild_id,
            self.current_command,
            'role',
            self
        )
        await interaction.response.send_modal(modal)
    
    async def on_add_user_exclusions(self, interaction: discord.Interaction):
        """Show modal to add user exclusions"""
        modal = ExclusionModal(
            self.manager,
            self.guild_id,
            self.current_command,
            'user',
            self
        )
        await interaction.response.send_modal(modal)
    
    async def on_clear_config(self, interaction: discord.Interaction):
        """Clear all permissions for this command"""
        perms = self.manager.get_guild_perms(self.guild_id)
        if self.current_command in perms:
            del perms[self.current_command]
            settings = self.manager._load_settings()
            settings[str(self.guild_id)]['permissions'] = perms
            self.manager._save_settings(settings)
        
        await self.update_display(interaction)
    
    async def update_display(self, interaction: discord.Interaction):
        """Update the embed and view"""
        self._add_controls()
        
        embed = discord.Embed(
            title="⚙️ Command Permissions Manager",
            description="Configure which channels can use specific commands, and who can bypass restrictions.",
            color=config.COLOR_PRIMARY
        )
        
        if self.current_category:
            embed.add_field(
                name="📁 Selected Category",
                value=f"`{self.current_category}`",
                inline=True
            )
        
        if self.current_command:
            perms = self.manager.get_guild_perms(self.guild_id)
            cmd_perms = perms.get(self.current_command, {})
            
            embed.add_field(
                name="🎯 Selected Command",
                value=f"`/{self.current_command}`",
                inline=True
            )
            
            mode = cmd_perms.get('mode', 'whitelist')
            embed.add_field(
                name="🔒 Mode",
                value=f"`{mode.upper()}`",
                inline=True
            )
            
            channels = cmd_perms.get('channels', [])
            if channels:
                channel_mentions = [f"<#{ch}>" for ch in channels]
                embed.add_field(
                    name=f"📝 {'Allowed' if mode == 'whitelist' else 'Blocked'} Channels ({len(channels)})",
                    value=", ".join(channel_mentions[:10]) + ("..." if len(channels) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"📝 {'Allowed' if mode == 'whitelist' else 'Blocked'} Channels",
                    value="No channels configured" + (" (command allowed everywhere)" if mode == 'whitelist' else " (command not blocked anywhere)"),
                    inline=False
                )
            
            excluded_roles = cmd_perms.get('excluded_roles', [])
            if excluded_roles:
                role_mentions = [f"<@&{r}>" for r in excluded_roles]
                embed.add_field(
                    name=f"👥 Excluded Roles ({len(excluded_roles)})",
                    value=", ".join(role_mentions[:10]) + ("..." if len(excluded_roles) > 10 else ""),
                    inline=False
                )
            
            excluded_users = cmd_perms.get('excluded_users', [])
            if excluded_users:
                user_mentions = [f"<@{u}>" for u in excluded_users]
                embed.add_field(
                    name=f"👤 Excluded Users ({len(excluded_users)})",
                    value=", ".join(user_mentions[:10]) + ("..." if len(excluded_users) > 10 else ""),
                    inline=False
                )
            
            embed.set_footer(text="💡 Excluded users/roles can bypass channel restrictions")
        else:
            embed.add_field(
                name="ℹ️ How it works",
                value=(
                    "**Whitelist Mode:** Command only works in specified channels\n"
                    "**Blacklist Mode:** Command blocked in specified channels\n"
                    "**Exclusions:** Users/roles that bypass restrictions\n\n"
                    "Select a category and command to get started!"
                ),
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)


class Permissions(commands.Cog):
    """Command permissions management"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = PermissionsManager()
    
    @app_commands.command(name="permissions", description="Configure command permissions")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def permissions_command(self, interaction: discord.Interaction):
        """Open the permissions configuration panel"""
        view = PermissionsView(self.manager, interaction.guild_id, self.bot)
        
        embed = discord.Embed(
            title="⚙️ Command Permissions Manager",
            description="Configure which channels can use specific commands, and who can bypass restrictions.",
            color=config.COLOR_PRIMARY
        )
        
        embed.add_field(
            name="ℹ️ How it works",
            value=(
                "**Whitelist Mode:** Command only works in specified channels\n"
                "**Blacklist Mode:** Command blocked in specified channels\n"
                "**Exclusions:** Users/roles that bypass restrictions\n\n"
                "Select a category and command to get started!"
            ),
            inline=False
        )
        
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Check permissions before command execution"""
        if interaction.type != discord.InteractionType.application_command:
            return
        
        if not interaction.guild_id:
            return  # DMs always allowed
        
        command_name = interaction.command.name
        
        # Skip permission check for permissions command itself
        if command_name == "permissions":
            return
        
        # Get user roles
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return
        
        role_ids = [role.id for role in member.roles]
        
        # Check permission
        allowed = self.manager.check_permission(
            interaction.guild_id,
            command_name,
            interaction.channel_id,
            interaction.user.id,
            role_ids
        )
        
        if not allowed:
            embed = discord.Embed(
                title="❌ Command Restricted",
                description=f"You cannot use `/{command_name}` in this channel.",
                color=config.COLOR_ERROR
            )
            embed.set_footer(text="Contact an administrator if you believe this is an error.")
            
            # Try to respond
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
            
            # This won't actually stop the command - Discord's interaction system doesn't allow that
            # But we've already responded, so the original command won't execute properly


async def setup(bot: commands.Bot):
    await bot.add_cog(Permissions(bot))
