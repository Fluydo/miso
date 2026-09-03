import logging
import discord
from discord.ext import commands

from functions.moderation import send_mod_log
from functions.message_cache import cache_message, get_cached_message
from embeds.logs import (
    create_message_delete_log_view,
    create_message_edit_log_view,
    create_avatar_update_log_view,
    create_name_update_log_view,
    create_channel_create_log_view,
    create_channel_delete_log_view,
    create_channel_update_log_view,
    create_role_create_log_view,
    create_role_delete_log_view,
    create_role_update_log_view,
    create_role_permissions_update_log_view,
    create_guild_update_log_view,
    member_join_log_embed,
    member_leave_log_embed,
    member_roles_update_log_embed,
    guild_update_log_embed,
)

logger = logging.getLogger("miso.cogs.events")


class Events(commands.Cog):
    """Event listeners for server audit and activity logging."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ==========================================
    # MESSAGE CACHING - Cache all messages for delete logs
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Cache every message with its embeds, components, and attachments."""
        if message.guild:
            cache_message(message)

    # ==========================================
    # MESSAGE EVENTS -> "messages" thread (Visual UI Images)
    # ==========================================
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if not message.guild:
            return
        
        # Skip if this message was bulk deleted (from /clear command)
        if hasattr(self.bot, '_bulk_deleted_messages') and message.id in self.bot._bulk_deleted_messages:
            self.bot._bulk_deleted_messages.discard(message.id)  # Remove from set
            return
        
        # Check if message is cached (has content/author data)
        if not message.author:
            logger.debug(f"Skipping delete log for uncached message {message.id}")
            return
        
        # Run in background
        async def send_log():
            try:
                # Try to get cached message data first
                cached = get_cached_message(message.guild.id, message.id)
                
                # If we have cached data, reconstruct the embeds from it
                original_embeds = []
                if cached and cached.get("embeds"):
                    for embed_dict in cached["embeds"]:
                        original_embeds.append(discord.Embed.from_dict(embed_dict))
                elif message.embeds:
                    # Fallback to message embeds if available
                    original_embeds = message.embeds[:10]
                
                view, file, _ = await create_message_delete_log_view(message)
                
                # Send the log with the reconstructed embeds
                await send_mod_log(
                    message.guild, 
                    log_type="messages", 
                    view=view, 
                    file=file,
                    embeds=original_embeds if original_embeds else None
                )
            except Exception as e:
                logger.error(f"Error generating visual delete log: {e}", exc_info=True)
        
        self.bot.loop.create_task(send_log())

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not before.guild:
            return
        if before.content == after.content:
            return
        
        # Run in background
        async def send_log():
            try:
                view, file = await create_message_edit_log_view(before, after)
                await send_mod_log(before.guild, log_type="messages", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual edit log: {e}", exc_info=True)
        
        self.bot.loop.create_task(send_log())

    # ==========================================
    # MEMBER JOIN & LEAVE -> "members" thread
    # ==========================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        embed = member_join_log_embed(member)
        await send_mod_log(member.guild, embed, log_type="members")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        embed = member_leave_log_embed(member)
        await send_mod_log(member.guild, embed, log_type="members")

    # ==========================================
    # MEMBER & USER PROFILE / NAME / ROLE UPDATES -> "profiles" thread
    # ==========================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        guild = after.guild

        # Nickname change (Visual Name Card)
        if before.nick != after.nick:
            try:
                view, file = await create_name_update_log_view(
                    user=after,
                    before_name=before.nick or before.name,
                    after_name=after.nick or after.name,
                    is_nick=True,
                )
                await send_mod_log(guild, log_type="profiles", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual nickname log: {e}", exc_info=True)

        # Server-specific avatar change (Visual Profile Card)
        if before.guild_avatar != after.guild_avatar:
            try:
                before_url = before.display_avatar.url
                after_url = after.display_avatar.url
                view, file = await create_avatar_update_log_view(after, before_url, after_url)
                await send_mod_log(guild, log_type="profiles", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual guild avatar log: {e}", exc_info=True)

        # Role change
        if before.roles != after.roles:
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]
            if added_roles or removed_roles:
                embed = member_roles_update_log_embed(after, added_roles, removed_roles)
                await send_mod_log(guild, embed, log_type="profiles")

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        # Username change (Visual Name Card)
        if before.name != after.name or getattr(before, "global_name", None) != getattr(after, "global_name", None):
            before_name = before.global_name or before.name
            after_name = after.global_name or after.name
            try:
                view, file = await create_name_update_log_view(
                    user=after,
                    before_name=before_name,
                    after_name=after_name,
                    is_nick=False,
                )
                for guild in self.bot.guilds:
                    if guild.get_member(after.id):
                        await send_mod_log(guild, log_type="profiles", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual username log: {e}", exc_info=True)

        # Global Avatar change (Visual Profile Card)
        if before.avatar != after.avatar:
            try:
                before_url = before.display_avatar.url
                after_url = after.display_avatar.url
                view, file = await create_avatar_update_log_view(after, before_url, after_url)
                for guild in self.bot.guilds:
                    if guild.get_member(after.id):
                        await send_mod_log(guild, log_type="profiles", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual avatar log: {e}", exc_info=True)

    # ==========================================
    # CHANNEL EVENTS -> "server" thread (Visual UI Images)
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        # Run in background to not block other events
        async def send_log():
            try:
                view, file = await create_channel_create_log_view(channel)
                await send_mod_log(channel.guild, log_type="server", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual channel create log: {e}", exc_info=True)
        
        self.bot.loop.create_task(send_log())

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        # Run in background to not block other events
        async def send_log():
            try:
                view, file = await create_channel_delete_log_view(channel)
                await send_mod_log(channel.guild, log_type="server", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual channel delete log: {e}", exc_info=True)
        
        self.bot.loop.create_task(send_log())

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self,
        before: discord.abc.GuildChannel,
        after: discord.abc.GuildChannel,
    ) -> None:
        # Channel Rename (Visual Discord Channel Pill)
        if before.name != after.name:
            # Run in background to not block other events
            async def send_log():
                try:
                    view, file = await create_channel_update_log_view(after, before.name, after.name)
                    await send_mod_log(after.guild, log_type="server", view=view, file=file)
                except Exception as e:
                    logger.error(f"Error generating visual channel update log: {e}", exc_info=True)
            
            self.bot.loop.create_task(send_log())

    # ==========================================
    # ROLE EVENTS -> "server" thread (Visual UI Images)
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        # Run in background
        async def send_log():
            try:
                view, file = await create_role_create_log_view(role)
                await send_mod_log(role.guild, log_type="server", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual role create log: {e}", exc_info=True)
        
        self.bot.loop.create_task(send_log())

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        # Run in background
        async def send_log():
            try:
                view, file = await create_role_delete_log_view(role)
                await send_mod_log(role.guild, log_type="server", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual role delete log: {e}", exc_info=True)
        
        self.bot.loop.create_task(send_log())

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        # 1. Role Name or Color update (Visual Discord Role Pill)
        if before.name != after.name or before.color != after.color:
            try:
                view, file = await create_role_update_log_view(
                    role=after,
                    before_name=before.name,
                    after_name=after.name,
                    before_color_hex=str(before.color),
                    after_color_hex=str(after.color),
                )
                await send_mod_log(after.guild, log_type="server", view=view, file=file)
            except Exception as e:
                logger.error(f"Error generating visual role update log: {e}", exc_info=True)

        # 2. Permission Updates (Visual Discord Permission Toggle Switches in ONE log)
        if before.permissions != after.permissions:
            b_perms = dict(before.permissions)
            a_perms = dict(after.permissions)
            changed_perms = []
            for perm_name, a_val in a_perms.items():
                b_val = b_perms.get(perm_name)
                if b_val != a_val:
                    readable_name = perm_name.replace("_", " ").title()
                    changed_perms.append({
                        "name": readable_name,
                        "was_enabled": b_val,
                        "now_enabled": a_val,
                    })

            if changed_perms:
                try:
                    view, file = await create_role_permissions_update_log_view(
                        role=after,
                        changed_perms=changed_perms,
                    )
                    await send_mod_log(after.guild, log_type="server", view=view, file=file)
                except Exception as e:
                    logger.error(f"Error generating visual role perm log: {e}", exc_info=True)

    # ==========================================
    # GUILD / SERVER UPDATE -> "server" thread
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        # Server Name update (Visual Server Card)
        if before.name != after.name:
            try:
                view, file = await create_guild_update_log_view(after, before.name, after.name)
                await send_mod_log(after, log_type="server", view=view, file=file)
                return
            except Exception as e:
                logger.error(f"Error generating visual guild update log: {e}", exc_info=True)

        changes = []
        if before.icon != after.icon:
            changes.append("Server Icon was updated.")
        if before.banner != after.banner:
            changes.append("Server Banner was updated.")
        if before.owner_id != after.owner_id:
            changes.append(f"Server Ownership transferred to <@{after.owner_id}>.")

        if changes:
            embed = guild_update_log_embed(after, changes)
            await send_mod_log(after, embed, log_type="server")

    # ==========================================
    # EMOJI EVENTS -> Sync to Supabase
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: list[discord.Emoji],
        after: list[discord.Emoji],
    ) -> None:
        """Sync emojis to Supabase when they're added/removed/updated."""
        logger.info(f"Emoji update detected in {guild.name}, syncing to Supabase...")
        
        # Trigger emoji sync
        if hasattr(self.bot, 'sync_emojis_to_supabase'):
            self.bot.loop.create_task(self.bot.sync_emojis_to_supabase())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
