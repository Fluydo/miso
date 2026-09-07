"""
cogs/bot_profile.py
Bot profile management commands.
"""

import io
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from functions.profile_randomizer import get_random_profile, get_profile_asset_path

logger = logging.getLogger("miso.cogs.bot_profile")


class BotProfileCog(commands.Cog):
    """Bot profile customization commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="randomize", description="Randomize the bot's profile in this server (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def randomize_profile(self, interaction: discord.Interaction) -> None:
        """Randomize bot profile with random name, pfp, and banner."""
        try:
            if not interaction.guild:
                await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            logger.info(f"Randomize command started for guild {interaction.guild.name}")
            # Get random profile
            display_name, pfp_filename, banner_filename = get_random_profile()

            # Upload assets to Supabase Storage if configured
            avatar_url = None
            banner_url = None

            if config.SUPABASE_SERVICE_KEY and config.SUPABASE_URL:
                from supabase import create_client
                supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

                # Upload pfp
                if pfp_filename:
                    pfp_path = get_profile_asset_path("pfps", pfp_filename)
                    if pfp_path:
                        try:
                            with open(pfp_path, 'rb') as f:
                                pfp_data = f.read()
                            
                            # Detect content type from extension
                            ext = pfp_path.suffix.lower()
                            content_type = 'image/png'
                            if ext == '.jpg' or ext == '.jpeg':
                                content_type = 'image/jpeg'
                            elif ext == '.gif':
                                content_type = 'image/gif'
                            
                            storage_path = f"{interaction.guild.id}/avatar_{pfp_filename}"
                            
                            # Delete old file if exists
                            try:
                                supabase.storage.from_('bot-profiles').remove([storage_path])
                            except:
                                pass
                            
                            # Upload new file
                            upload_result = supabase.storage.from_('bot-profiles').upload(
                                storage_path,
                                pfp_data,
                                file_options={"content-type": content_type}
                            )
                            
                            # Get public URL
                            public_url_result = supabase.storage.from_('bot-profiles').get_public_url(storage_path)
                            avatar_url = public_url_result
                            logger.info(f"Uploaded pfp to: {avatar_url}")
                        except Exception as e:
                            logger.error(f"Failed to upload pfp: {e}", exc_info=True)

                # Upload banner
                if banner_filename:
                    banner_path = get_profile_asset_path("banners", banner_filename)
                    if banner_path:
                        try:
                            with open(banner_path, 'rb') as f:
                                banner_data = f.read()
                            
                            # Detect content type from extension
                            ext = banner_path.suffix.lower()
                            content_type = 'image/png'
                            if ext == '.jpg' or ext == '.jpeg':
                                content_type = 'image/jpeg'
                            elif ext == '.gif':
                                content_type = 'image/gif'
                            
                            storage_path = f"{interaction.guild.id}/banner_{banner_filename}"
                            
                            # Delete old file if exists
                            try:
                                supabase.storage.from_('bot-profiles').remove([storage_path])
                            except:
                                pass
                            
                            # Upload new file
                            upload_result = supabase.storage.from_('bot-profiles').upload(
                                storage_path,
                                banner_data,
                                file_options={"content-type": content_type}
                            )
                            
                            # Get public URL
                            public_url_result = supabase.storage.from_('bot-profiles').get_public_url(storage_path)
                            banner_url = public_url_result
                            logger.info(f"Uploaded banner to: {banner_url}")
                        except Exception as e:
                            logger.error(f"Failed to upload banner: {e}", exc_info=True)

                # Update bot profile in database
                try:
                    profile_data = {
                        'guild_id': str(interaction.guild.id),
                        'enabled': True,
                        'display_name': display_name,
                        'avatar_url': avatar_url,
                        'banner_url': banner_url,
                        'description': f'Randomly generated profile',
                    }
                    
                    supabase.table('bot_profiles').upsert(profile_data, on_conflict='guild_id').execute()
                    logger.info(f"Updated bot profile in database for guild {interaction.guild.id}")
                except Exception as e:
                    logger.error(f"Failed to update bot profile in database: {e}")

            # Apply the profile (change nickname)
            try:
                bot_member = interaction.guild.get_member(self.bot.user.id)
                if bot_member:
                    await bot_member.edit(nick=display_name)
                    logger.info(f"Changed bot nickname to '{display_name}' in guild {interaction.guild.name}")
            except discord.Forbidden:
                logger.warning(f"Missing permission to change nickname in guild {interaction.guild.name}")
            except Exception as e:
                logger.error(f"Failed to change nickname: {e}")

            # Send confirmation embed
            embed = discord.Embed(
                title="🎲 Bot Profile Randomized!",
                description=f"I've been given a fresh new look in this server!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Name", value=f"`{display_name}`", inline=False)
            
            if avatar_url:
                embed.add_field(name="Avatar", value="✅ Updated", inline=True)
                embed.set_thumbnail(url=avatar_url)
            
            if banner_url:
                embed.add_field(name="Banner", value="✅ Updated", inline=True)
                embed.set_image(url=banner_url)
            
            embed.set_footer(text="View the full profile in the dashboard at /server/{guild_id}/bot-profile")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in randomize command: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"❌ Failed to randomize profile: {str(e)}", ephemeral=True)
            except:
                logger.error("Failed to send error message to user")


async def setup(bot: commands.Bot) -> None:
    cog = BotProfileCog(bot)
    await bot.add_cog(cog)
    
    @cog.randomize_profile.error
    async def randomize_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in randomize command: {error}", exc_info=error)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ An error occurred: {str(error)}", ephemeral=True)
            except:
                pass
