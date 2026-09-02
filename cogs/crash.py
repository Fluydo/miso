import discord
from discord import app_commands
from discord.ext import commands
import config


class CrashButton(discord.ui.View):
    """Button to open crash game on website"""
    def __init__(self):
        super().__init__(timeout=None)
        button = discord.ui.Button(
            label="🎰 Play Crash Game",
            url="https://miso-dashboard-iota.vercel.app/games/crash",
            style=discord.ButtonStyle.link
        )
        self.add_item(button)


class Crash(commands.Cog):
    """Crash game - play on website"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="crash", description="Play the crash game on the website")
    async def crash_info(self, interaction: discord.Interaction):
        """View crash game info and link to website"""
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🚀 Crash Game",
            description=(
                f"**How to Play:**\n"
                f"{config.EMOJI_CHEVRON_RIGHT} Place a bet before the round starts\n"
                f"{config.EMOJI_CHEVRON_RIGHT} Watch the multiplier climb\n"
                f"{config.EMOJI_CHEVRON_RIGHT} Cash out before it crashes!\n"
                f"{config.EMOJI_CHEVRON_RIGHT} The higher you wait, the more you win (or lose!)\n\n"
                f"**Play on our website for the full experience with:**\n"
                f"• Live animated graphics\n"
                f"• Real-time multiplier\n"
                f"• Leaderboards\n"
                f"• Bet history\n\n"
                f"Click the button below to start playing!"
            ),
            color=config.COLOR_PRIMARY
        )
        embed.set_footer(text="Good luck! 🎰")
        
        view = CrashButton()
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Crash(bot))
