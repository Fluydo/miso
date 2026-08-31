import re
from datetime import timedelta

TIME_REGEX = re.compile(r"(?:(\d+)\s*w)?\s*(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?", re.IGNORECASE)

TIME_UNITS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
}


def parse_duration(duration_str: str) -> timedelta:
    """
    Parses human-readable duration strings into a datetime.timedelta.
    Supported units: s (seconds), m (minutes), h (hours), d (days), w (weeks).
    Examples: '10m', '2h', '7d', '1w2d', '30s'.
    Raises ValueError on invalid formats or empty duration.
    """
    if not duration_str or not duration_str.strip():
        raise ValueError("Duration string cannot be empty.")

    cleaned_str = duration_str.strip().lower()
    
    # Check for simple pattern or multi-segment pattern
    # e.g., '10m', '1d12h'
    matches = re.findall(r"(\d+)\s*([smhdw])", cleaned_str)
    
    # Ensure the entire string matched tokens
    reconstructed = "".join(f"{amount}{unit}" for amount, unit in matches)
    no_space_input = re.sub(r"\s+", "", cleaned_str)
    
    if not matches or reconstructed != no_space_input:
        raise ValueError(
            f"Invalid duration format: `{duration_str}`. "
            "Use formats like `10m`, `2h`, `7d`, `1w`, or `1d12h`."
        )

    total_seconds = 0
    for amount_str, unit in matches:
        amount = int(amount_str)
        if amount <= 0:
            raise ValueError(f"Duration values must be greater than zero.")
        total_seconds += amount * TIME_UNITS[unit]

    if total_seconds <= 0:
        raise ValueError("Duration must be greater than 0 seconds.")

    # Discord maximum timeout limit is 28 days (2,419,200 seconds)
    return timedelta(seconds=total_seconds)


def format_duration(td: timedelta) -> str:
    """
    Formats a timedelta into a clean human-readable string.
    """
    total_seconds = int(td.total_seconds())
    if total_seconds <= 0:
        return "0s"

    weeks, remainder = divmod(total_seconds, 604800)
    days, remainder = divmod(remainder, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if weeks > 0:
        parts.append(f"{weeks}w")
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0:
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0s"
