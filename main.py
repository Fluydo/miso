"""
MAIN.PY WITH STOP CHECK (FOR OLD PC ONLY!)

This version checks for STOP_SIGNAL.txt and shuts down if detected.
Only rename this to main.py on the OLD PC!

DO NOT USE ON THIS PC - keep your original main.py
"""

import asyncio
import logging
import sys
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from embeds.errors import error_embed, permission_error_embed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("miso.main")


class MisoBot(commands.Bot):
    """Core Miso Bot instance."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.messages = True  # Required to cache messages for delete/edit logs

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            max_messages=10000,  # Cache up to 10k messages for delete/edit logs
        )
        
        # Start STOP signal checker
        self.stop_check_task = None

    async def setup_hook(self) -> None:
        """Asynchronously load all cogs and sync slash commands."""
        cogs_dir = config.BASE_DIR / "cogs"
        logger.info("Loading extensions from cogs directory...")

        for file in cogs_dir.glob("*.py"):
            if file.name.startswith("__"):
                continue
            cog_name = f"cogs.{file.stem}"
            try:
                await self.load_extension(cog_name)
                logger.info(f"Loaded extension: {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog_name}: {e}", exc_info=True)

        self.tree.on_error = self.on_app_command_error

    async def _force_sync(self) -> dict:
        """Force-clear and re-sync commands to all dev guilds + globally. Returns counts."""
        results = {}

        for guild_id in config.DEV_GUILD_IDS:
            guild_obj = discord.Object(id=guild_id)
            try:
                self.tree.clear_commands(guild=guild_obj)
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                results[guild_id] = len(synced)
                logger.info(f"Force-synced {len(synced)} commands to guild {guild_id}.")
            except Exception as e:
                logger.warning(f"Could not sync commands to dev guild {guild_id}: {e}")
                results[guild_id] = -1

        try:
            global_synced = await self.tree.sync()
            results["global"] = len(global_synced)
            logger.info(f"Force-synced {len(global_synced)} commands globally.")
        except Exception as e:
            logger.error(f"Failed global sync: {e}", exc_info=True)
            results["global"] = -1

        return results

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Global error handler for all slash command invocations."""
        if isinstance(error, app_commands.MissingPermissions):
            missing = ", ".join(f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions)
            embed = permission_error_embed(missing)
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing = ", ".join(f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions)
            embed = error_embed(
                f"I do not have the required permissions in this server to perform this action.\n\n**Missing:** {missing}",
                title="⛔ Bot Permission Missing",
            )
        elif isinstance(error, app_commands.CommandOnCooldown):
            embed = error_embed(
                f"This command is currently on cooldown. Please retry in `{error.retry_after:.1f}` seconds.",
                title="⏳ Cooldown Active",
            )
        elif isinstance(error, app_commands.CheckFailure):
            embed = error_embed("You do not meet the requirements to run this command.")
        else:
            logger.error(f"Unhandled app command error in /{interaction.command.name if interaction.command else 'unknown'}: {error}", exc_info=error)
            embed = error_embed(
                "An unexpected error occurred while executing this command. Please try again later."
            )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def check_stop_signal(self):
        """Check for STOP_SIGNAL.txt and shutdown if found."""
        stop_signal_path = config.BASE_DIR / "STOP_SIGNAL.txt"
        
        if stop_signal_path.exists():
            try:
                with open(stop_signal_path, 'r') as f:
                    content = f.read().strip()
                
                if content.startswith("STOP"):
                    logger.critical("=" * 60)
                    logger.critical("🛑 STOP SIGNAL DETECTED!")
                    logger.critical("Shutting down bot as requested...")
                    logger.critical("=" * 60)
                    await self.close()
                    sys.exit(0)
            except Exception as e:
                logger.error(f"Error reading STOP_SIGNAL.txt: {e}")

    async def on_ready(self) -> None:
        """Executed once the bot is connected and ready."""
        divider = "=" * 55
        logger.info(divider)
        logger.info(f"  {config.BOT_NAME} Bot is Online and Ready!")
        logger.info(f"  Logged in as : {self.user.name} ({self.user.id})")
        logger.info(f"  discord.py   : v{discord.__version__}")
        logger.info(f"  Guilds       : {len(self.guilds)}")
        logger.info(f"  Latency      : {self.latency * 1000:.2f}ms")
        logger.info(divider)
        logger.info("🛑 STOP signal monitoring ENABLED")
        logger.info("   Bot will shutdown if STOP_SIGNAL.txt is detected")
        logger.info(divider)

        # Start STOP signal checker (every 10 seconds)
        if not self.stop_check_task or self.stop_check_task.done():
            @tasks.loop(seconds=10)
            async def stop_checker():
                await self.check_stop_signal()
            
            self.stop_check_task = stop_checker
            self.stop_check_task.start()
            logger.info("Started STOP signal checker (checks every 10s)")

        # Force sync all slash commands to dev guilds + globally on startup
        logger.info("Syncing slash commands on ready...")
        results = await self._force_sync()
        for gid, count in results.items():
            if count == -1:
                logger.warning(f"Sync failed for {gid}")
            else:
                logger.info(f"Synced {count} commands to {gid}")

        # Set rich presence activity
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="/help | Protecting the server",
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        # Start Supabase giveaway poller for bidirectional sync
        if config.SUPABASE_SERVICE_KEY and config.SUPABASE_URL:
            from functions.supabase_poller import GiveawayPoller
            if not hasattr(self, 'giveaway_poller'):
                self.giveaway_poller = GiveawayPoller(self)
                await self.giveaway_poller.start()
                logger.info("Started Supabase giveaway poller")
        else:
            logger.warning("SUPABASE_SERVICE_KEY not set, skipping giveaway poller")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_commands(self, ctx: commands.Context) -> None:
        """Owner-only: Force clear and re-sync all slash commands immediately."""
        msg = await ctx.send("🔄 Force syncing slash commands...")
        results = await self._force_sync()

        lines = []
        for gid, count in results.items():
            label = "Global" if gid == "global" else f"Guild `{gid}`"
            if count == -1:
                lines.append(f"❌ {label}: sync failed")
            else:
                lines.append(f"✅ {label}: `{count}` commands synced")

        await msg.edit(content="**Slash Command Sync Results:**\n" + "\n".join(lines))


def main() -> None:
    """Entry point for starting Miso Bot."""
    if not config.BOT_TOKEN:
        logger.critical(
            "DISCORD_TOKEN is missing or not set in .env! "
            "Please create a .env file based on .env.example and provide your bot token."
        )
        sys.exit(1)

    # Auto-install Node.js dependencies for GIF generation
    logger.info("Checking Node.js dependencies...")
    try:
        import subprocess
        node_modules = config.BASE_DIR / "node_modules"
        package_json = config.BASE_DIR / "package.json"
        
        if package_json.exists() and (not node_modules.exists() or not (node_modules / "puppeteer").exists()):
            logger.info("Installing Node.js dependencies (puppeteer)...")
            result = subprocess.run(
                ["npm", "install"],
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("✅ Node.js dependencies installed successfully")
            else:
                logger.warning(f"⚠️ npm install failed (will use fallback renderer): {result.stderr}")
        else:
            logger.info("✅ Node.js dependencies already installed")
    except FileNotFoundError:
        logger.warning("⚠️ npm not found in PATH - install Node.js to enable advanced GIF rendering")
    except Exception as e:
        logger.warning(f"⚠️ Could not install Node.js dependencies: {e}")

    bot = MisoBot()

    try:
        bot.run(config.BOT_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.critical("Invalid Discord Bot Token provided in .env! Please check your credentials.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot shutting down via KeyboardInterrupt...")


if __name__ == "__main__":
    main()
