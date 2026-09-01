"""
functions/supabase_poller.py
Polls Supabase for giveaway entry changes and syncs to Discord embeds.
"""

import asyncio
import logging
from typing import Dict, Set

import httpx
import discord

import config

logger = logging.getLogger("miso.functions.supabase_poller")


class GiveawayPoller:
    """Polls Supabase for giveaway entry changes and updates Discord messages."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.known_entries: Dict[str, Set[str]] = {}  # message_id -> set of discord_ids
        self.running = False

    async def start(self):
        """Start the polling loop."""
        if self.running:
            return
        self.running = True
        logger.info("Starting Supabase giveaway poller")
        asyncio.create_task(self._poll_loop())

    def stop(self):
        """Stop the polling loop."""
        self.running = False
        logger.info("Stopping Supabase giveaway poller")

    async def _poll_loop(self):
        """Poll Supabase every 5 seconds for entry changes."""
        while self.running:
            try:
                await self._check_entries()
            except Exception as e:
                logger.error(f"Error polling Supabase: {e}")
            await asyncio.sleep(5)  # Poll every 5 seconds

    async def _check_entries(self):
        """Check Supabase for entry changes and update Discord embeds."""
        if not config.SUPABASE_SERVICE_KEY or not config.SUPABASE_URL:
            return

        headers = {
            "apikey": config.SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all active giveaways
            resp = await client.get(
                f"{config.SUPABASE_URL}/rest/v1/giveaways?active=eq.true&select=id,message_id,guild_id,channel_id",
                headers=headers,
            )
            if resp.status_code != 200:
                return

            giveaways = resp.json()

            for giveaway in giveaways:
                message_id = giveaway["message_id"]
                guild_id = int(giveaway["guild_id"])
                channel_id = int(giveaway["channel_id"])
                giveaway_id = giveaway["id"]

                # Get entries from Supabase
                entries_resp = await client.get(
                    f"{config.SUPABASE_URL}/rest/v1/giveaway_entries?giveaway_id=eq.{giveaway_id}&select=discord_id",
                    headers=headers,
                )
                if entries_resp.status_code != 200:
                    continue

                entries = entries_resp.json()
                current_entries = {entry["discord_id"] for entry in entries}

                # Check if entries changed
                if message_id not in self.known_entries:
                    self.known_entries[message_id] = current_entries
                    continue

                if current_entries != self.known_entries[message_id]:
                    # Entries changed! Update the Discord message
                    logger.info(f"Giveaway {message_id} entries changed: {len(self.known_entries[message_id])} -> {len(current_entries)}")
                    self.known_entries[message_id] = current_entries
                    await self._update_discord_message(guild_id, channel_id, int(message_id), len(current_entries))

    async def _update_discord_message(self, guild_id: int, channel_id: int, message_id: int, entry_count: int):
        """Update the Discord giveaway message with new entry count."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                return

            message = await channel.fetch_message(message_id)
            if not message or not message.embeds:
                return

            # Update the embed's footer with new count
            embed = message.embeds[0]
            old_footer = embed.footer.text if embed.footer else ""
            
            # Update entry count in footer
            if "entries" in old_footer.lower():
                # Parse and update the count
                parts = old_footer.split("|")
                updated_parts = []
                for part in parts:
                    if "entries" in part.lower():
                        updated_parts.append(f" {entry_count} entries ")
                    else:
                        updated_parts.append(part)
                new_footer = "|".join(updated_parts)
            else:
                # Add entry count if not present
                new_footer = f"{old_footer} | {entry_count} entries"

            embed.set_footer(text=new_footer, icon_url=embed.footer.icon_url if embed.footer else None)

            # Update the view button count
            from cogs.giveaways import GiveawayView
            view = GiveawayView(message_id, entry_count)

            await message.edit(embed=embed, view=view)
            logger.info(f"Updated Discord message {message_id} with {entry_count} entries")

        except discord.NotFound:
            logger.warning(f"Message {message_id} not found, removing from poller")
            if str(message_id) in self.known_entries:
                del self.known_entries[str(message_id)]
        except Exception as e:
            logger.error(f"Error updating Discord message {message_id}: {e}")
