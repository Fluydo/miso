import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Bot Credentials
BOT_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# Bot Metadata
BOT_NAME: str = "Miso"

# Guild IDs where slash commands are synced instantly on startup (dev/prod servers)
DEV_GUILD_IDS: list[int] = [1543920075097251850, 1179061609767903292]
BOT_VERSION: str = "1.0.0"
BOT_DESCRIPTION: str = "A modern, high-performance moderation and utility bot for Discord."

# Paths
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"
WARNINGS_FILE: Path = DATA_DIR / "warnings.json"
TEMPBANS_FILE: Path = DATA_DIR / "tempbans.json"
SETTINGS_FILE: Path = DATA_DIR / "guild_settings.json"
INVITES_FILE: Path = DATA_DIR / "invites.json"
ECONOMY_FILE: Path = DATA_DIR / "economy.json"
TICKETS_FILE: Path = DATA_DIR / "tickets.json"
LEVELS_FILE: Path = DATA_DIR / "levels.json"
WELCOME_FILE: Path = DATA_DIR / "welcome.json"
ANTINUKE_FILE: Path = DATA_DIR / "antinuke.json"
GIVEAWAYS_FILE: Path = DATA_DIR / "giveaways.json"
VERIFICATION_FILE: Path = DATA_DIR / "verification.json"

# Custom Emojis - Core Actions & UI
EMOJI_TICK: str = "<:tick:1543926260659650600>"
EMOJI_CROSS: str = "<:cross:1543927801655070831>"
EMOJI_WARN: str = "<:warn:1543930876193275966>"
EMOJI_DOTSTAR: str = "<:dotstar:1543945907819647047>"
EMOJI_GEAR: str = "<a:gear:1543949547502440508>"
EMOJI_INFO: str = "<:i_info:1543952345883475978>"
EMOJI_HASHTAG: str = "<:Hastag:1543953535794806784>"
EMOJI_NAME: str = "<:name:1543955523811016734>"
EMOJI_PFP: str = "<:pfp:1543955486548828240>"
EMOJI_CHEVRON_RIGHT: str = "<:chevronright:1543959632291303434>"
EMOJI_MOVE_RIGHT: str = "<:moveright:1543960615603937421>"
EMOJI_ARROW_RIGHT: str = "<:arrowright:1543960661258670220>"
EMOJI_DOUBLE_CHEVRON: str = "<:doublechevronright:1543972486654468177>"

# Custom Emojis - Economy & Minigames
EMOJI_COIN: str = "<a:coin:1543993161464942662>"
EMOJI_MINES_BOMB: str = "<:mines_bomb:1543993969212653709>"
EMOJI_MINES_GEM: str = "<:mines_gem:1543993632191676416>"

# Custom Emojis - Tickets
EMOJI_TICKET: str = "<:ticket:1544010178267971676>"
EMOJI_TICKET_PURPLE: str = "<:ticket_purple:1544004296813711463>"
EMOJI_APPLICATION_PURPLE: str = "<:application_purple:1544004295534444648>"
EMOJI_REPORT_PURPLE: str = "<:report_purple:1544004298218934272>"

# Custom Emojis - Specific Logs
EMOJI_MEMBER_JOIN: str = "<:member_join:1543962149330624532>"
EMOJI_MEMBER_LEFT: str = "<:member_left:1543962150450499695>"
EMOJI_BAN_LOGS: str = "<:ban_logs:1543974574536790076>"
EMOJI_TEMPBAN_LOGS: str = "<:tempban_logs:1543974579171631175>"
EMOJI_KICK_LOGS: str = "<:kick_logs:1543974575837155438>"
EMOJI_TIMEOUT_LOGS: str = "<:timeout_logs:1543974580375392346>"
EMOJI_UNBAN_LOGS: str = "<:unban_logs:1543974581532884992>"
EMOJI_WARN_LOGS: str = "<:warn_logs:1543974582699040908>"
EMOJI_MESSAGE_DELETE_LOGS: str = "<:message_delete_logs:1543974576915218573>"
EMOJI_MESSAGE_EDIT_LOGS: str = "<:message_edit_logs:1543974578001551491>"

# Embed Colors
COLOR_PRIMARY: int = 0xA240F7    # Purple / Brand
COLOR_SUCCESS: int = 0x57F287    # Green (Unbans, Clears, Success)
COLOR_WARNING: int = 0xFEE75C    # Yellow (Warnings, Timeouts)
COLOR_ERROR: int = 0xED4245      # Red (Bans, Kicks, Errors)
COLOR_INFO: int = 0xA240F7       # Information / Theme
