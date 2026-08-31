import discord
import config


def error_embed(message: str, title: str | None = None) -> discord.Embed:
    """Standardized error embed without footer/timestamp."""
    description = f"{config.EMOJI_CROSS} {message}"
    return discord.Embed(
        title=title,
        description=description,
        color=config.COLOR_ERROR,
    )


def permission_error_embed(missing_permission: str) -> discord.Embed:
    """Embed returned when a user lacks required permissions."""
    description = f"{config.EMOJI_CROSS} You do not have permission to execute this command. Missing: `{missing_permission}`"
    return discord.Embed(
        title=None,
        description=description,
        color=config.COLOR_ERROR,
    )


def hierarchy_error_embed(reason: str) -> discord.Embed:
    """Embed returned when role hierarchy prevents moderation."""
    description = f"{config.EMOJI_CROSS} {reason}"
    return discord.Embed(
        title=None,
        description=description,
        color=config.COLOR_ERROR,
    )
