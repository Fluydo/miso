"""
functions/renderer.py
Renders Discord UI components to PNG images with completely transparent backgrounds using Playwright.
Includes:
- Discord message delete / edit with clan tags, revealed spoilers, and parsed mentions
- Multi-message Purge / Clear transcript card with clan chips, replied-to headers, and APP badges
- Moderation action cards (Ban, Kick, Timeout, Warn, Unban)
- Anti-Nuke trigger quarantine card
- Verification log card
- Welcome and Leave cards
- Leveling Rank card
- 3x3, 4x4, and 5x5 Mines board
- 3-segment transparent rounded Slots frame
- Blackjack card table (transparent background)
- Coinflip & Roulette outcome cards
- Tower climber minigame board
- Leaderboard cards (Economy, Invites, Levels)
"""

import asyncio
import html
import io
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import Browser, Playwright, async_playwright

logger = logging.getLogger("miso.renderer")

# Reusable browser singleton
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_browser_lock = asyncio.Lock()

# Discord CDN Emoji Assets
GEM_CDN_URL = "https://cdn.discordapp.com/emojis/1543993632191676416.png"
BOMB_CDN_URL = "https://cdn.discordapp.com/emojis/1543993969212653709.png"


async def _get_browser() -> Browser:
    """Ensures a shared headless Chromium instance is active."""
    global _playwright, _browser
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            if _playwright is None:
                _playwright = await async_playwright().start()
            try:
                _browser = await _playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
                )
            except Exception:
                # Browser binary missing — auto-install it then retry
                logger.warning("Playwright browser not found — running 'playwright install chromium'...")
                import subprocess, sys
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,
                )
                _browser = await _playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
                )
    return _browser


def _escape(text: str) -> str:
    """Escapes HTML characters in text."""
    return html.escape(text or "")


def _hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    """Converts hex color string to rgba() CSS string."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    return f"rgba(153, 170, 181, {alpha})"


def _format_role_color(color_hex: str) -> tuple[str, str, str]:
    if not color_hex or color_hex.lower() in ("#000000", "#0", "0"):
        color = "#dbdee1"
        bg = "rgba(78, 80, 88, 0.25)"
        border = "rgba(255, 255, 255, 0.1)"
    else:
        color = color_hex if color_hex.startswith("#") else f"#{color_hex}"
        bg = _hex_to_rgba(color, 0.15)
        border = _hex_to_rgba(color, 0.35)
    return color, bg, border


def _render_markdown(raw_text: str) -> str:
    """Discord markdown parser to HTML with opened spoilers and resolved mentions."""
    if not raw_text:
        return "<span style='color:#949ba4; font-style:italic;'>No text content</span>"
    
    # 1. Resolve raw Discord pings/mentions
    text = re.sub(r'<@!?\d+>', r'@user', raw_text)
    text = re.sub(r'<@&\d+>', r'@role', text)
    text = re.sub(r'<#\d+>', r'#channel', text)
    text = re.sub(r'<a?:(\w+):\d+>', r':\1:', text)

    text = _escape(text)

    text = re.sub(r'```(?:[a-zA-Z0-9_-]+)?\n?([\s\S]*?)```', r'<pre><code>\1</code></pre>', text)
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__([^_]+)__', r'<u>\1</u>', text)
    text = re.sub(r'~~([^~]+)~~', r'<s>\1</s>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'(^|[^\w])_([^_]+)_([^\w]|$)', r'\1<em>\2</em>\3', text)
    
    # Revealed / opened spoilers
    text = re.sub(r'\|\|([^|]+)\|\|', r'<span class="spoiler">\1</span>', text)
    text = re.sub(r'^&gt; (.*)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)
    text = re.sub(r'(@\w+)', r'<span class="mention">\1</span>', text)
    text = re.sub(r'(#\w+)', r'<span class="mention">\1</span>', text)

    parts = text.split('<pre>')
    formatted = []
    for i, p in enumerate(parts):
        if i == 0:
            formatted.append(p.replace('\n', '<br>'))
        else:
            if '</code></pre>' in p:
                code_part, rest = p.split('</code></pre>', 1)
                formatted.append('<pre>' + code_part + '</code></pre>' + rest.replace('\n', '<br>'))
            else:
                formatted.append('<pre>' + p)
    return "".join(formatted)


def _render_clan_chip(clan_tag: str | None, clan_badge_url: str | None) -> str:
    """Renders the Discord server clan tag pill (e.g. MOAN)."""
    if not clan_tag:
        return ""
    badge_html = f'<img src="{clan_badge_url}" alt="" onerror="this.style.display=\'none\';">' if clan_badge_url else ""
    return f"""
    <span class="clan-chip">
        {badge_html}
        <span>{_escape(clan_tag)}</span>
    </span>
    """


def _render_bot_tag(is_bot: bool, is_verified: bool = False) -> str:
    if not is_bot:
        return ""
    check_svg = '<svg style="width:11px; height:11px; margin-left:2px; vertical-align:middle;" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>' if is_verified else ""
    return f'<span class="bot-badge">APP{check_svg}</span>'


DISCORD_CHANNEL_SVGS = {
    "text": '<span style="font-weight:700; font-size:16px; color:#949ba4; line-height:1; font-family:monospace;">#</span>',
    "voice": '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3.5C11.66 3.34 11.26 3.42 11 3.7L6.5 8H3C2.45 8 2 8.45 2 9V15C2 15.55 2.45 16 3 16H6.5L11 20.3C11.26 20.58 11.66 20.66 12 20.5C12.34 20.34 12.56 20 12.56 19.6V4.4C12.56 4 12.34 3.66 12 3.5ZM16.5 12C16.5 10.23 15.48 8.71 14 7.97V16.02C15.48 15.29 16.5 13.77 16.5 12ZM14 3.23V5.29C16.89 6.15 19 8.83 19 12C19 15.17 16.89 17.85 14 18.71V20.77C18.01 19.86 21 16.28 21 12C21 7.72 18.01 4.14 14 3.23Z"/></svg>',
    "forum": '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" clip-rule="evenodd" d="M3.75 3C2.7835 3 2 3.7835 2 4.75V15.25C2 16.2165 2.7835 17 3.75 17H5V20.25C5 20.8023 5.44772 21.25 6 21.25C6.26522 21.25 6.51957 21.1446 6.70711 20.9571L10.6642 17H16.25C17.2165 17 18 16.2165 18 15.25V4.75C18 3.7835 17.2165 3 16.25 3H3.75ZM20 7H20.25C21.2165 7 22 7.7835 22 8.75V19.25C22 20.2165 21.2165 21 20.25 21H18.75V22.25C18.75 22.8023 18.3023 23.25 17.75 23.25C17.4848 23.25 17.2304 23.1446 17.0429 22.9571L14.7929 20.7071C14.6054 20.5196 14.5 20.2652 14.5 20H10C9.44772 20 9 19.5523 9 19C9 18.4477 9.44772 18 10 18H14.75C15.7165 18 16.5 17.2165 16.5 16.25V7H20Z"/></svg>',
    "category": '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M16.59 8.59004L12 13.17L7.41 8.59004L6 10L12 16L18 10L16.59 8.59004Z"/></svg>',
    "announcement": '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V15H13V17ZM13 13H11V7H13V13Z"/></svg>',
}


_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: transparent;
    font-family: 'Inter', 'gg sans', 'Noto Sans', Helvetica, Arial, sans-serif;
    padding: 8px;
    display: inline-block;
    color: #dbdee1;
    -webkit-font-smoothing: antialiased;
}

.card {
    background: transparent;
    border: none;
    padding: 4px 6px;
    min-width: 320px;
    max-width: 600px;
}

/* Replied-To Line */
.replied-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: 18px;
    margin-bottom: 3px;
    position: relative;
    font-size: 12.5px;
    color: #b5bac1;
}

.replied-spine {
    position: absolute;
    left: -14px;
    top: 8px;
    width: 14px;
    height: 9px;
    border-left: 2px solid #4e5058;
    border-top: 2px solid #4e5058;
    border-top-left-radius: 6px;
}

.replied-avatar {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    object-fit: cover;
}

.replied-author {
    font-weight: 600;
    color: #f2f3f5;
}

.replied-content {
    color: #949ba4;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    max-width: 350px;
}

.msg-row {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 2px 0;
}

.avatar {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
}

.msg-body {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex: 1;
    min-width: 0;
}

.msg-header {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.username {
    color: #f2f3f5;
    font-weight: 600;
    font-size: 15.5px;
    line-height: 1.2;
}

.bot-badge {
    background: #5865f2;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    line-height: 1.2;
    letter-spacing: 0.3px;
    display: inline-flex;
    align-items: center;
}

.clan-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(79, 84, 92, 0.48);
    border-radius: 4px;
    padding: 1px 6px 1px 4px;
    vertical-align: middle;
}

.clan-chip img {
    width: 14px;
    height: 14px;
    border-radius: 2px;
    object-fit: cover;
}

.clan-chip span {
    color: #dbdee1;
    font-size: 11.5px;
    font-weight: 600;
    line-height: 14px;
    letter-spacing: 0.2px;
}

.timestamp {
    color: #949ba4;
    font-size: 12px;
    font-weight: 500;
    margin-left: 2px;
}

.edited-tag {
    color: #949ba4;
    font-size: 10.5px;
    font-weight: 400;
    margin-left: 4px;
}

.msg-content {
    color: #dbdee1;
    font-size: 15px;
    line-height: 1.4;
    word-break: break-word;
}

.msg-content strong { font-weight: 700; color: #fff; }
.msg-content em { font-style: italic; }
.msg-content u { text-decoration: underline; }
.msg-content s { text-decoration: line-through; opacity: 0.7; }
.msg-content code {
    background: #1e1f22;
    border: 1px solid #2b2d31;
    border-radius: 4px;
    padding: 2px 5px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13.5px;
    color: #e3e5e8;
}
.msg-content pre {
    background: #1e1f22;
    border: 1px solid #2b2d31;
    border-radius: 6px;
    padding: 8px 12px;
    overflow-x: auto;
    margin: 6px 0;
}
.msg-content pre code { background: none; border: none; padding: 0; }
.msg-content blockquote {
    border-left: 4px solid #4e5058;
    padding-left: 10px;
    margin: 4px 0;
    color: #949ba4;
}
.msg-content .mention {
    background: rgba(88, 101, 242, 0.25);
    color: #c9cdfb;
    border-radius: 3px;
    padding: 1px 4px;
    font-weight: 500;
}

/* Revealed Spoilers */
.msg-content .spoiler {
    background: rgba(255, 255, 255, 0.08);
    color: #dbdee1;
    border: 1px dashed rgba(255, 255, 255, 0.25);
    border-radius: 4px;
    padding: 0 5px;
}

/* Arrow Divider */
.arrow-divider {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 8px 0;
}

.arrow-circle {
    width: 32px;
    height: 32px;
    background: #2b2d31;
    border: 1px solid #3f4147;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.45);
    flex-shrink: 0;
}

/* Horizontal Name Change */
.name-change-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 6px 10px;
}

.name-user-side {
    display: flex;
    align-items: center;
    gap: 10px;
}

.name-user-side .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
}

.name-text {
    font-size: 15.5px;
    line-height: 1.2;
}

.name-text.old { color: #ed4245; font-weight: 600; }
.name-text.new { color: #57f287; font-weight: 600; }

.channel-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(78, 80, 88, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 6px 12px;
    border-radius: 6px;
    color: #dbdee1;
    font-weight: 600;
    font-size: 15px;
}
.channel-pill.old { color: #ed4245; }
.channel-pill.new { color: #57f287; }

.role-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14.5px;
}

.role-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* Moderation / Trigger Card */
.mod-card {
    background: rgba(30, 31, 35, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 18px;
    min-width: 360px;
}

.mod-avatar {
    width: 54px;
    height: 54px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
}

.mod-details {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.mod-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    width: fit-content;
}

.mod-user {
    font-size: 16px;
    font-weight: 700;
    color: #f2f3f5;
}

.mod-reason {
    font-size: 13.5px;
    color: #949ba4;
}

/* Leaderboard Card */
.lb-card {
    background: rgba(30, 31, 35, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 360px;
    max-width: 460px;
}

.lb-title {
    font-size: 16px;
    font-weight: 700;
    color: #f2f3f5;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.lb-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 6px;
    border-radius: 8px;
}

.lb-user-info {
    display: flex;
    align-items: center;
    gap: 10px;
}

.lb-rank {
    font-weight: 700;
    font-size: 14px;
    width: 24px;
    text-align: center;
}

.lb-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    object-fit: cover;
}

.lb-name {
    font-size: 14px;
    font-weight: 600;
    color: #dbdee1;
}

.lb-value {
    font-size: 14px;
    font-weight: 700;
    color: #57f287;
}

/* Welcome & Leave Cards */
.greet-card {
    background: rgba(24, 34, 46, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 20px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    min-width: 380px;
}

.greet-avatar {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #5865f2;
}

.greet-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.greet-title {
    font-size: 18px;
    font-weight: 800;
    color: #ffffff;
}

.greet-sub {
    font-size: 13.5px;
    color: #949ba4;
}

/* Rank / Level Card */
.rank-card {
    background: rgba(24, 34, 46, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 18px;
    min-width: 380px;
}

.rank-avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    object-fit: cover;
}

.rank-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
}

.rank-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.rank-name {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
}

.rank-numbers {
    font-size: 13px;
    font-weight: 700;
    color: #a240f7;
}

.rank-bar-bg {
    width: 100%;
    height: 10px;
    background: #2b2d31;
    border-radius: 5px;
    overflow: hidden;
}

.rank-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #a240f7, #5865f2);
    border-radius: 5px;
}

/* Role Permission Toggle Switches */
.perm-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 320px;
}

.perm-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 8px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.03);
}

.perm-title {
    font-size: 13.5px;
    font-weight: 500;
    color: #dbdee1;
    flex: 1;
    margin-right: 12px;
}

.discord-toggle {
    width: 40px;
    height: 22px;
    border-radius: 11px;
    position: relative;
    flex-shrink: 0;
    transition: background 0.2s;
}

.discord-toggle.on {
    background: #23a559;
}

.discord-toggle.off {
    background: #4e5058;
}

.toggle-knob {
    position: absolute;
    top: 3px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    transition: left 0.2s;
}

.discord-toggle.on .toggle-knob {
    left: 21px;
}

.discord-toggle.off .toggle-knob {
    left: 3px;
}

/* Server icon for server update card */
.server-side {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-direction: column;
}

.server-icon-img {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    object-fit: cover;
}
"""


async def _capture_html(html_content: str, element_id: str = "#target") -> bytes:
    """Renders HTML in headless Chromium and captures target element with transparent background."""
    browser = await _get_browser()
    page = await browser.new_page(viewport={"width": 800, "height": 800})
    try:
        await page.set_content(html_content, wait_until="networkidle")
        target = page.locator(element_id)
        png_bytes = await target.screenshot(omit_background=True)
        return png_bytes
    finally:
        await page.close()


# ==========================================
# RENDER FUNCTIONS (MESSAGES & PROFILES)
# ==========================================

async def render_deleted_message(
    author_name: str,
    avatar_url: str,
    content: str,
    clan_tag: str | None = None,
    clan_badge_url: str | None = None,
    timestamp_str: str | None = None,
    is_bot: bool = False,
    is_verified_bot: bool = False,
    replied_to: dict | None = None,
) -> bytes:
    ts = timestamp_str or datetime.now(timezone.utc).strftime("Today at %I:%M %p")
    html_body = _render_markdown(content)
    clan_chip_html = _render_clan_chip(clan_tag, clan_badge_url)
    bot_badge = _render_bot_tag(is_bot, is_verified_bot)

    reply_html = ""
    if replied_to:
        reply_html = f"""
        <div class="replied-header">
            <div class="replied-spine"></div>
            <img class="replied-avatar" src="{replied_to.get('avatar_url', '')}">
            <span class="replied-author">@{_escape(replied_to.get('author_name', ''))}</span>
            <span class="replied-content">{_escape(replied_to.get('content', ''))}</span>
        </div>
        """

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card">
            {reply_html}
            <div class="msg-row">
                <img class="avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <div class="msg-body">
                    <div class="msg-header">
                        <span class="username">{_escape(author_name)}</span>
                        {bot_badge}
                        {clan_chip_html}
                        <span class="timestamp">{_escape(ts)}</span>
                    </div>
                    <div class="msg-content">{html_body}</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_edited_message(
    author_name: str,
    avatar_url: str,
    before_content: str,
    after_content: str,
    clan_tag: str | None = None,
    clan_badge_url: str | None = None,
    timestamp_str: str | None = None,
    is_bot: bool = False,
    is_verified_bot: bool = False,
) -> bytes:
    ts = timestamp_str or datetime.now(timezone.utc).strftime("Today at %I:%M %p")
    before_html = _render_markdown(before_content)
    after_html = _render_markdown(after_content)
    clan_chip_html = _render_clan_chip(clan_tag, clan_badge_url)
    bot_badge = _render_bot_tag(is_bot, is_verified_bot)

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" style="display: flex; flex-direction: column; gap: 2px;">
            <div class="card">
                <div class="msg-row">
                    <img class="avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                    <div class="msg-body">
                        <div class="msg-header">
                            <span class="username">{_escape(author_name)}</span>
                            {bot_badge}
                            {clan_chip_html}
                            <span class="timestamp">{_escape(ts)}</span>
                        </div>
                        <div class="msg-content" style="opacity: 0.85;">{before_html}</div>
                    </div>
                </div>
            </div>

            <div class="arrow-divider">
                <div class="arrow-circle">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a240f7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <polyline points="19 12 12 19 5 12"></polyline>
                    </svg>
                </div>
            </div>

            <div class="card">
                <div class="msg-row">
                    <img class="avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                    <div class="msg-body">
                        <div class="msg-header">
                            <span class="username">{_escape(author_name)}</span>
                            {bot_badge}
                            {clan_chip_html}
                            <span class="timestamp">{_escape(ts)}</span>
                        </div>
                        <div class="msg-content">{after_html}<span class="edited-tag">(edited)</span></div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_purged_messages(messages_data: list[dict]) -> bytes:
    rows_html = []
    for m in messages_data:
        author_name = m.get("author_name", "User")
        avatar_url = m.get("avatar_url", "")
        content = m.get("content", "")
        ts = m.get("timestamp_str", "")
        is_bot = m.get("is_bot", False)
        clan_tag = m.get("clan_tag")
        clan_badge_url = m.get("clan_badge_url")
        bot_badge = _render_bot_tag(is_bot)
        clan_chip = _render_clan_chip(clan_tag, clan_badge_url)
        html_body = _render_markdown(content)

        reply_html = ""
        replied_to = m.get("replied_to")
        if replied_to:
            reply_html = f"""
            <div class="replied-header">
                <div class="replied-spine"></div>
                <img class="replied-avatar" src="{replied_to.get('avatar_url', '')}">
                <span class="replied-author">@{_escape(replied_to.get('author_name', ''))}</span>
                <span class="replied-content">{_escape(replied_to.get('content', ''))}</span>
            </div>
            """

        rows_html.append(f"""
        <div style="margin-bottom: 8px;">
            {reply_html}
            <div class="msg-row">
                <img class="avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <div class="msg-body">
                    <div class="msg-header">
                        <span class="username">{_escape(author_name)}</span>
                        {bot_badge}
                        {clan_chip}
                        <span class="timestamp">{_escape(ts)}</span>
                    </div>
                    <div class="msg-content">{html_body}</div>
                </div>
            </div>
        </div>
        """)

    all_rows = "".join(rows_html)

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 10px;">
            {all_rows}
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_moderation_action(
    action_name: str,
    target_name: str,
    target_avatar_url: str,
    mod_name: str,
    reason: str,
    duration: str | None = None,
    badge_color: str = "#ed4245",
) -> bytes:
    dur_html = f'<span style="color:#f2f3f5; font-weight:600;"> • {duration}</span>' if duration else ""

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="mod-card">
            <img class="mod-avatar" src="{target_avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="mod-details">
                <div class="mod-badge" style="background: {_hex_to_rgba(badge_color, 0.2)}; color: {badge_color}; border: 1px solid {_hex_to_rgba(badge_color, 0.4)};">
                    <span>{_escape(action_name)}</span>
                </div>
                <div class="mod-user">{_escape(target_name)}{dur_html}</div>
                <div class="mod-reason"><strong>Reason:</strong> {_escape(reason)}</div>
                <div style="font-size: 12px; color: #72767d;">Moderator: @{_escape(mod_name)}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_antinuke_trigger(
    mod_name: str,
    mod_avatar_url: str,
    action_type: str,
    count: int,
    threshold: int,
) -> bytes:
    """Renders Anti-Nuke quarantine alert card."""
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="mod-card" style="border: 1.5px solid #ed4245;">
            <img class="mod-avatar" src="{mod_avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="mod-details">
                <div class="mod-badge" style="background: rgba(237, 66, 69, 0.2); color: #ed4245; border: 1px solid #ed4245;">
                    <span>🛡️ ANTI-NUKE QUARANTINE</span>
                </div>
                <div class="mod-user">@{_escape(mod_name)}</div>
                <div class="mod-reason"><strong>Trigger:</strong> Rapid {action_type} ({count}/{threshold} in 10s)</div>
                <div style="font-size: 12px; color: #57f287;">Action Taken: Stripped administrative & moderator roles.</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_verify_log(
    user_name: str,
    avatar_url: str,
    verified_at_str: str,
) -> bytes:
    """Renders visual member verified log card."""
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="mod-card" style="border: 1px solid rgba(87, 242, 135, 0.3);">
            <img class="mod-avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="mod-details">
                <div class="mod-badge" style="background: rgba(87, 242, 135, 0.2); color: #57f287; border: 1px solid rgba(87, 242, 135, 0.4);">
                    <span>MEMBER VERIFIED</span>
                </div>
                <div class="mod-user">@{_escape(user_name)}</div>
                <div class="mod-reason">Completed server verification panel.</div>
                <div style="font-size: 12px; color: #72767d;">Timestamp: {_escape(verified_at_str)}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_welcome_card(
    avatar_url: str,
    username: str,
    member_count: int,
    server_name: str,
) -> bytes:
    """Renders transparent Welcome greeting card."""
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="greet-card">
            <img class="greet-avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="greet-info">
                <div class="greet-title">Welcome to {_escape(server_name)}!</div>
                <div style="font-size: 15px; font-weight: 600; color: #57f287;">@{_escape(username)}</div>
                <div class="greet-sub">You are member <strong>#{member_count}</strong></div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_leave_card(
    avatar_url: str,
    username: str,
    duration_str: str,
    server_name: str,
) -> bytes:
    """Renders transparent Member Leave card."""
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="greet-card" style="border-color: rgba(237, 66, 69, 0.25);">
            <img class="greet-avatar" style="border-color: #ed4245;" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="greet-info">
                <div class="greet-title">Goodbye from {_escape(server_name)}</div>
                <div style="font-size: 15px; font-weight: 600; color: #ed4245;">@{_escape(username)}</div>
                <div class="greet-sub">Was in server for: <strong>{_escape(duration_str)}</strong></div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_rank_card(
    avatar_url: str,
    username: str,
    level: int,
    current_xp: int,
    required_xp: int,
    rank_pos: int,
) -> bytes:
    """Renders transparent Level & Rank card."""
    pct = min(100, max(0, int((current_xp / max(1, required_xp)) * 100)))

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="rank-card">
            <img class="rank-avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="rank-body">
                <div class="rank-header">
                    <span class="rank-name">{_escape(username)}</span>
                    <span class="rank-numbers">RANK #{rank_pos} • LVL {level}</span>
                </div>
                <div class="rank-bar-bg">
                    <div class="rank-bar-fill" style="width: {pct}%;"></div>
                </div>
                <div style="font-size: 11.5px; color: #949ba4; display: flex; justify-content: space-between;">
                    <span>Progress</span>
                    <span>{current_xp:,} / {required_xp:,} XP ({pct}%)</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_avatar_change(before_avatar_url: str, after_avatar_url: str) -> bytes:
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 12px;">
            <div class="pfp-container" style="display:flex; align-items:center; justify-content:center; gap:22px;">
                <img style="width:96px; height:96px; border-radius:18px; object-fit:cover;" src="{before_avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <div class="arrow-circle" style="width: 36px; height: 36px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a240f7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </div>
                <img style="width:96px; height:96px; border-radius:18px; object-fit:cover;" src="{after_avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_name_change(avatar_url: str, before_name: str, after_name: str) -> bytes:
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 8px;">
            <div class="name-change-container">
                <div class="name-user-side">
                    <img class="avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                    <span class="name-text old">{_escape(before_name)}</span>
                </div>
                <div class="arrow-circle" style="width: 28px; height: 28px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a240f7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </div>
                <div class="name-user-side">
                    <img class="avatar" src="{avatar_url}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                    <span class="name-text new">{_escape(after_name)}</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_channel_pill(channel_name: str, channel_type: str = "text", is_deleted: bool = False) -> bytes:
    svg_icon = DISCORD_CHANNEL_SVGS.get(channel_type, DISCORD_CHANNEL_SVGS["text"])
    status_class = "channel-pill old" if is_deleted else "channel-pill new"
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 8px;">
            <div class="{status_class}">{svg_icon}<span>{_escape(channel_name)}</span></div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_channel_update(before_name: str, after_name: str, channel_type: str = "text") -> bytes:
    svg_icon = DISCORD_CHANNEL_SVGS.get(channel_type, DISCORD_CHANNEL_SVGS["text"])
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 8px;">
            <div class="name-change-container">
                <div class="channel-pill old">{svg_icon}<span>{_escape(before_name)}</span></div>
                <div class="arrow-circle" style="width: 28px; height: 28px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a240f7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </div>
                <div class="channel-pill new">{svg_icon}<span>{_escape(after_name)}</span></div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_role_pill(role_name: str, role_color_hex: str, is_deleted: bool = False) -> bytes:
    color, bg, border = _format_role_color(role_color_hex)
    status_class = "role-pill old" if is_deleted else "role-pill"
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 8px;">
            <div class="{status_class}" style="color: {color}; background: {bg}; border: 1px solid {border};">
                <span class="role-dot" style="background: {color};"></span>
                <span>{_escape(role_name)}</span>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_role_update(before_name: str, after_name: str, before_color_hex: str, after_color_hex: str) -> bytes:
    b_color, b_bg, b_border = _format_role_color(before_color_hex)
    a_color, a_bg, a_border = _format_role_color(after_color_hex)
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 8px;">
            <div class="name-change-container">
                <div class="role-pill old" style="color: {b_color}; background: {b_bg}; border: 1px solid {b_border};">
                    <span class="role-dot" style="background: {b_color};"></span>
                    <span>{_escape(before_name)}</span>
                </div>
                <div class="arrow-circle" style="width: 28px; height: 28px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a240f7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </div>
                <div class="role-pill" style="color: {a_color}; background: {a_bg}; border: 1px solid {a_border};">
                    <span class="role-dot" style="background: {a_color};"></span>
                    <span>{_escape(after_name)}</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_role_permissions_update(
    role_name: str,
    role_color_hex: str,
    changed_perms: list[dict],
) -> bytes:
    color, bg, border = _format_role_color(role_color_hex)
    rows_html = []
    for p in changed_perms:
        p_name = p["name"]
        before_class = "discord-toggle on" if p["was_enabled"] else "discord-toggle off"
        after_class = "discord-toggle on" if p["now_enabled"] else "discord-toggle off"
        rows_html.append(f"""
        <div class="perm-row">
            <span class="perm-title">{_escape(p_name)}</span>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div class="{before_class}"><div class="toggle-knob"></div></div>
                <div class="arrow-circle" style="width: 22px; height: 22px;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a240f7" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </div>
                <div class="{after_class}"><div class="toggle-knob"></div></div>
            </div>
        </div>
        """)
    all_rows = "".join(rows_html)

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 4px 6px; display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; align-items: center;">
                <div class="role-pill" style="color: {color}; background: {bg}; border: 1px solid {border}; padding: 4px 10px; font-size: 13.5px;">
                    <span class="role-dot" style="background: {color}; width: 8px; height: 8px;"></span>
                    <span>{_escape(role_name)}</span>
                </div>
            </div>
            <div class="perm-list">{all_rows}</div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_server_update(before_name: str, after_name: str, icon_url: str | None = None) -> bytes:
    img_tag = f'<img class="server-icon-img" src="{icon_url}">' if icon_url else '<div class="server-icon-img" style="background: #5865f2; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; color: #fff;">S</div>'
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="card" style="padding: 6px 10px;">
            <div class="name-change-container">
                <div class="server-side">{img_tag}<span class="name-text old">{_escape(before_name)}</span></div>
                <div class="arrow-circle" style="width: 32px; height: 32px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a240f7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </div>
                <div class="server-side">{img_tag}<span class="name-text new">{_escape(after_name)}</span></div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


# ==========================================
# RENDER FUNCTIONS (LEADERBOARDS)
# ==========================================

async def render_leaderboard_card(
    title: str,
    entries: list[dict],
    page: int,
    total_pages: int,
) -> bytes:
    rows_html = []
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for e in entries:
        r = e["rank"]
        rank_badge = medals.get(r, f"#{r}")
        name = _escape(e["name"])
        val = _escape(e["value_str"])
        avatar = e.get("avatar_url", "")

        rows_html.append(f"""
        <div class="lb-row">
            <div class="lb-user-info">
                <span class="lb-rank">{rank_badge}</span>
                <img class="lb-avatar" src="{avatar}" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <span class="lb-name">{name}</span>
            </div>
            <span class="lb-value">{val}</span>
        </div>
        """)

    all_rows = "".join(rows_html)

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" class="lb-card">
            <div class="lb-title">
                <span>{_escape(title)}</span>
                <span style="font-size:12px; color:#949ba4;">Page {page}/{total_pages}</span>
            </div>
            {all_rows}
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


# ==========================================
# RENDER FUNCTIONS (MINES MINIGAME BOARD)
# ==========================================

_MINES_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: transparent;
    font-family: Arial, sans-serif;
    color: white;
    padding: 8px;
    display: inline-block;
}

.game {
    background: transparent;
    border: none;
    box-shadow: none;
    padding: 4px;
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.stats {
    display: flex;
    align-items: center;
    justify-content: space-around;
    height: 38px;
    background: rgba(24, 34, 46, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 0 16px;
}

.stat {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #dce2e9;
}

.stat.profit { color: #4f9cff; }

.grid { display: grid; gap: 8px; }
.grid.grid-3 { grid-template-columns: repeat(3, 76px); grid-template-rows: repeat(3, 76px); }
.grid.grid-4 { grid-template-columns: repeat(4, 66px); grid-template-rows: repeat(4, 66px); }
.grid.grid-5 { grid-template-columns: repeat(5, 58px); grid-template-rows: repeat(5, 58px); }

.tile {
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: 10px;
    background: #303943;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

.tile.safe { background: #1e293b; border: 1.5px solid #22c55e; }
.tile.mine { background: #451a1a; border: 1.5px solid #ef4444; }

.tile.safe .glow {
    position: absolute;
    width: 60%;
    height: 60%;
    border-radius: 50%;
    background: #22c55e;
    filter: blur(14px);
    opacity: 0.75;
}

.tile.mine .glow {
    position: absolute;
    width: 60%;
    height: 60%;
    border-radius: 50%;
    background: #ef4444;
    filter: blur(14px);
    opacity: 0.75;
}

.icon-img {
    width: 70%;
    height: 70%;
    position: relative;
    z-index: 2;
    object-fit: contain;
}
"""


async def render_mines_board(
    tiles_state: list[str],
    gems_left: int,
    bombs_count: int,
    profit_text: str,
    multiplier_text: str,
    grid_size: int = 5,
) -> bytes:
    grid_class = f"grid-{grid_size}"
    tiles_html = []
    for state in tiles_state:
        if state == "gem":
            tiles_html.append(
                f'<div class="tile safe"><div class="glow"></div><img class="icon-img" src="{GEM_CDN_URL}"></div>'
            )
        elif state == "bomb":
            tiles_html.append(
                f'<div class="tile mine"><div class="glow"></div><img class="icon-img" src="{BOMB_CDN_URL}"></div>'
            )
        else:
            tiles_html.append('<div class="tile"></div>')

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_MINES_CSS}</style></head>
    <body>
        <div id="target" class="game">
            <div class="stats">
                <div class="stat">
                    <img src="{GEM_CDN_URL}" style="width: 20px; height: 20px; object-fit: contain;">
                    <span>{gems_left}</span>
                </div>
                <div class="stat">
                    <img src="{BOMB_CDN_URL}" style="width: 20px; height: 20px; object-fit: contain;">
                    <span>{bombs_count}</span>
                </div>
                <div class="stat profit">
                    <span>📈 {multiplier_text}</span>
                    <span>({profit_text})</span>
                </div>
            </div>
            <div class="grid {grid_class}">{"".join(tiles_html)}</div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


# ==========================================
# RENDER FUNCTIONS (SLOTS - 3-SEGMENT COMPACT)
# ==========================================

_SLOTS_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: transparent;
    font-family: 'Inter', Arial, sans-serif;
    color: white;
    padding: 0;
    margin: 0;
    display: inline-block;
}

.slots-frame {
    background: rgba(30, 31, 35, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    display: grid;
    grid-template-columns: repeat(3, 62px);
    height: 62px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

.slot-segment {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.slot-segment:last-child {
    border-right: none;
}
"""


async def render_slots_machine(reels: list[str]) -> bytes:
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_SLOTS_CSS}</style></head>
    <body>
        <div id="target" class="slots-frame">
            <div class="slot-segment">{reels[0]}</div>
            <div class="slot-segment">{reels[1]}</div>
            <div class="slot-segment">{reels[2]}</div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


# ==========================================
# RENDER FUNCTIONS (BLACKJACK - TRANSPARENT BG)
# ==========================================

_BLACKJACK_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: transparent;
    font-family: 'Inter', Arial, sans-serif;
    color: white;
    padding: 8px;
    display: inline-block;
}

.bj-table {
    background: transparent;
    border: none;
    box-shadow: none;
    padding: 4px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-width: 320px;
}

.hand-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.hand-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13.5px;
    font-weight: 700;
    color: #949ba4;
}

.cards-row {
    display: flex;
    gap: 8px;
}

.bj-card {
    width: 48px;
    height: 68px;
    background: #ffffff;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    padding: 4px;
    font-weight: 800;
    font-size: 14px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.3);
}

.bj-card.red { color: #ef4444; }
.bj-card.black { color: #1e1f22; }

.bj-card.hidden {
    background: #5865f2;
    border: 2px solid #ffffff;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 20px;
}
"""


async def render_blackjack_table(
    dealer_cards: list[dict],
    dealer_score: str,
    player_cards: list[dict],
    player_score: str,
) -> bytes:
    def _render_cards(cards: list[dict]) -> str:
        res = []
        for c in cards:
            if c.get("hidden"):
                res.append('<div class="bj-card hidden">🂠</div>')
            else:
                color_class = "red" if c.get("is_red") else "black"
                res.append(f"""
                <div class="bj-card {color_class}">
                    <span style="align-self:flex-start;">{c['rank']}</span>
                    <span style="font-size:20px; line-height:1;">{c['suit']}</span>
                    <span style="align-self:flex-end;">{c['rank']}</span>
                </div>
                """)
        return "".join(res)

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BLACKJACK_CSS}</style></head>
    <body>
        <div id="target" class="bj-table">
            <div class="hand-section">
                <div class="hand-header">
                    <span>DEALER'S HAND</span>
                    <span style="color:#f2f3f5;">Total: {dealer_score}</span>
                </div>
                <div class="cards-row">{_render_cards(dealer_cards)}</div>
            </div>

            <div style="height:1px; background:rgba(255,255,255,0.08);"></div>

            <div class="hand-section">
                <div class="hand-header">
                    <span>YOUR HAND</span>
                    <span style="color:#57f287;">Total: {player_score}</span>
                </div>
                <div class="cards-row">{_render_cards(player_cards)}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


# ==========================================
# RENDER FUNCTIONS (COINFLIP, ROULETTE & TOWER)
# ==========================================

async def render_coinflip_card(
    outcome: str,  # "heads" or "tails"
    won: bool,
    bet: int,
    payout: int,
) -> bytes:
    """Renders visual Coinflip outcome card."""
    coin_emoji = "🪙"
    status_text = f"WON +{payout} coins" if won else f"LOST -{bet} coins"
    status_color = "#57f287" if won else "#ed4245"

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" style="background: rgba(24, 34, 46, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px 24px; display: flex; align-items: center; gap: 16px; min-width: 280px;">
            <div style="width: 58px; height: 58px; background: #2b2d31; border: 2px solid #e6b000; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; box-shadow: 0 0 16px rgba(230,176,0,0.4);">
                {coin_emoji}
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="font-size: 16px; font-weight: 800; text-transform: uppercase; color: #ffffff;">{outcome}</div>
                <div style="font-size: 13.5px; font-weight: 700; color: {status_color};">{status_text}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_roulette_card(
    number: int,
    color_name: str,  # "red", "black", "green"
    won: bool,
    payout_text: str,
) -> bytes:
    """Renders Roulette outcome card with colored number pocket."""
    bg_map = {"red": "#ef4444", "black": "#1e1f22", "green": "#22c55e"}
    bg_color = bg_map.get(color_name, "#1e1f22")

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
    <body>
        <div id="target" style="background: rgba(24, 34, 46, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px 22px; display: flex; align-items: center; gap: 18px; min-width: 300px;">
            <div style="width: 60px; height: 60px; background: {bg_color}; border: 2px solid #ffffff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 900; color: #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.5);">
                {number}
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="font-size: 15px; font-weight: 800; text-transform: uppercase; color: #ffffff;">Landed on {color_name.upper()} {number}</div>
                <div style="font-size: 13px; font-weight: 700; color: {'#57f287' if won else '#ed4245'};">{payout_text}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_tower_board(
    floors_data: list[list[str]],  # list of 8 floors, each [tile1, tile2, tile3] ("safe", "skull", "hidden")
    current_floor: int,
    multiplier_text: str,
    profit_text: str,
) -> bytes:
    """Renders multi-floor Tower Climber minigame board."""
    rows_html = []
    for floor_idx in range(len(floors_data) - 1, -1, -1):
        floor_tiles = floors_data[floor_idx]
        tiles_div = []
        for t in floor_tiles:
            if t == "safe":
                tiles_div.append(f'<div class="tile safe" style="width:48px; height:36px;"><div class="glow"></div><img class="icon-img" src="{GEM_CDN_URL}"></div>')
            elif t == "skull":
                tiles_div.append(f'<div class="tile mine" style="width:48px; height:36px;"><div class="glow"></div><img class="icon-img" src="{BOMB_CDN_URL}"></div>')
            else:
                is_active = (floor_idx == current_floor)
                border_style = "border: 1.5px solid #a240f7;" if is_active else ""
                tiles_div.append(f'<div class="tile" style="width:48px; height:36px; {border_style}"></div>')
        
        rows_html.append(f"""
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 24px; font-size: 12px; font-weight: 700; color: #949ba4;">F{floor_idx + 1}</span>
            <div style="display: flex; gap: 6px;">{"".join(tiles_div)}</div>
        </div>
        """)

    doc = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><style>{_MINES_CSS}</style></head>
    <body>
        <div id="target" class="game" style="gap: 10px;">
            <div class="stats" style="min-width: 220px;">
                <div class="stat profit">
                    <span>📈 {multiplier_text}</span>
                    <span>({profit_text})</span>
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
                {"".join(rows_html)}
            </div>
        </div>
    </body>
    </html>
    """
    return await _capture_html(doc)


async def render_crash_frame(
    phase: str,
    multiplier: float = 1.0,
    countdown: int = 10,
    bet_list: list[dict] = None,
) -> bytes:
    """
    Renders a crash game frame with rocket animation and bet list.
    
    Args:
        phase: 'betting', 'running', 'supersonic', or 'crashed'
        multiplier: Current multiplier (for running/supersonic phase)
        countdown: Seconds remaining in betting phase
        bet_list: List of bets [{'username': str, 'amount': int, 'status': str, 'multiplier': float}]
    
    Returns:
        PNG bytes with transparent background
    """
    bet_list = bet_list or []
    
    # Rocket SVG with animation based on phase
    if phase == 'betting':
        # Rocket on launch pad with countdown
        rocket_y = 280
        rocket_rotation = 0
        rocket_color = "#5865f2"
        flame_opacity = 0.3
        bg_gradient_start = "#2b2d31"
        bg_gradient_end = "#1e1f22"
        title_text = f"🎰 BETTING PHASE"
        subtitle_text = f"Game starts in {countdown}s"
        title_color = "#fee75c"
    elif phase == 'running':
        # Rocket flying upward
        rocket_y = 150 - (multiplier * 10)  # Moves up as multiplier increases
        rocket_rotation = -10
        rocket_color = "#57f287"
        flame_opacity = 0.8
        bg_gradient_start = "#1e3a28"
        bg_gradient_end = "#0f1e14"
        title_text = f"🚀 FLYING"
        subtitle_text = f"{multiplier:.2f}x"
        title_color = "#57f287"
    elif phase == 'supersonic':
        # Rocket supersonic with orange glow
        rocket_y = 80
        rocket_rotation = -20
        rocket_color = "#ff9500"
        flame_opacity = 1.0
        bg_gradient_start = "#3a2010"
        bg_gradient_end = "#1e1008"
        title_text = f"🔥 SUPERSONIC"
        subtitle_text = f"{multiplier:.2f}x"
        title_color = "#ff9500"
    else:  # crashed
        # Explosion effect
        rocket_y = 200
        rocket_rotation = 45
        rocket_color = "#ed4245"
        flame_opacity = 0
        bg_gradient_start = "#3a1010"
        bg_gradient_end = "#1e0808"
        title_text = f"💥 CRASHED!"
        subtitle_text = f"at {multiplier:.2f}x"
        title_color = "#ed4245"
    
    # Generate bet list HTML
    bet_rows_html = ""
    for i, bet in enumerate(bet_list[:10]):  # Show top 10
        username = _escape(bet.get('username', 'Unknown'))
        amount = bet.get('amount', 0)
        status = bet.get('status', 'active')
        bet_mult = bet.get('multiplier', 0)
        
        if status == 'cashed_out':
            status_html = f'<span style="color:#57f287;">✓ {bet_mult:.2f}x</span>'
        elif status == 'lost':
            status_html = f'<span style="color:#ed4245;">✗ Lost</span>'
        else:
            status_html = f'<span style="color:#fee75c;">⏳ Active</span>'
        
        bet_rows_html += f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 10px; background:rgba(255,255,255,0.03); border-radius:6px; margin-bottom:4px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="color:#949ba4; font-size:13px; font-weight:700; width:20px;">#{i+1}</span>
                <span style="color:#dbdee1; font-size:14px; font-weight:600;">{username[:12]}</span>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="color:#a240f7; font-size:14px; font-weight:700;">{amount:,}</span>
                {status_html}
            </div>
        </div>
        """
    
    if not bet_rows_html:
        bet_rows_html = '<div style="text-align:center; color:#72767d; font-size:13px; padding:20px;">No bets yet</div>'
    
    # Rocket SVG graphic
    rocket_svg = f"""
    <svg width="80" height="120" viewBox="0 0 80 120" style="position:absolute; left:300px; top:{rocket_y}px; transform:rotate({rocket_rotation}deg); filter:drop-shadow(0 0 20px {rocket_color});">
        <!-- Rocket body -->
        <ellipse cx="40" cy="60" rx="18" ry="35" fill="{rocket_color}" opacity="0.9"/>
        <ellipse cx="40" cy="45" rx="16" ry="25" fill="{rocket_color}"/>
        
        <!-- Rocket nose cone -->
        <path d="M 40 10 L 25 35 L 55 35 Z" fill="{rocket_color}" stroke="#ffffff" stroke-width="1.5"/>
        
        <!-- Window -->
        <circle cx="40" cy="40" r="8" fill="#1e1f22" opacity="0.8"/>
        <circle cx="40" cy="40" r="6" fill="#5865f2" opacity="0.6"/>
        
        <!-- Fins -->
        <path d="M 22 70 L 10 90 L 22 85 Z" fill="{rocket_color}" opacity="0.8"/>
        <path d="M 58 70 L 70 90 L 58 85 Z" fill="{rocket_color}" opacity="0.8"/>
        
        <!-- Flame trail -->
        <ellipse cx="40" cy="95" rx="12" ry="20" fill="#ff6b1a" opacity="{flame_opacity}"/>
        <ellipse cx="40" cy="100" rx="8" ry="15" fill="#ffd700" opacity="{flame_opacity}"/>
        <ellipse cx="40" cy="105" rx="5" ry="10" fill="#ffffff" opacity="{flame_opacity * 0.8}"/>
    </svg>
    """
    
    doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: transparent;
            font-family: 'Inter', 'gg sans', sans-serif;
            color: #dbdee1;
            padding: 20px;
        }}
        .crash-container {{
            display: flex;
            gap: 20px;
            background: linear-gradient(135deg, {bg_gradient_start} 0%, {bg_gradient_end} 100%);
            border: 2px solid rgba(255,255,255,0.08);
            border-radius: 20px;
            padding: 24px;
            min-width: 800px;
        }}
        .bet-list {{
            width: 280px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .bet-list-title {{
            font-size: 16px;
            font-weight: 800;
            color: #f2f3f5;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
        }}
        .game-display {{
            flex: 1;
            position: relative;
            min-height: 400px;
            background: rgba(0,0,0,0.2);
            border-radius: 16px;
            border: 2px solid rgba(255,255,255,0.05);
            overflow: hidden;
        }}
        .game-title {{
            position: absolute;
            top: 30px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 32px;
            font-weight: 900;
            color: {title_color};
            text-shadow: 0 0 20px {title_color}, 0 4px 8px rgba(0,0,0,0.8);
            text-align: center;
            z-index: 10;
        }}
        .game-subtitle {{
            position: absolute;
            top: 75px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 48px;
            font-weight: 900;
            color: #ffffff;
            text-shadow: 0 0 30px {title_color}, 0 6px 12px rgba(0,0,0,0.9);
            z-index: 10;
        }}
        </style>
    </head>
    <body>
        <div id="target" class="crash-container">
            <div class="bet-list">
                <div class="bet-list-title">🎯 Active Bets ({len(bet_list)})</div>
                {bet_rows_html}
            </div>
            <div class="game-display">
                <div class="game-title">{title_text}</div>
                <div class="game-subtitle">{subtitle_text}</div>
                {rocket_svg}
            </div>
        </div>
    </body>
    </html>
    """
    
    return await _capture_html(doc)


def generate_crash_gif(
    phase: str,
    multiplier: float = 1.0,
    start_mult: float = 1.0,
    countdown: int = 10,
    bets: list = None,
    fps: int = 15,
    output_path: str = "crash_temp.gif"
) -> str:
    """
    Generate animated GIF using Puppeteer + HTML renderer.
    Falls back to PIL if Node.js fails.
    """
    import subprocess
    import os
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bot_dir = os.path.dirname(script_dir)  # Go up one level to bot root
    
    node_script = os.path.join(bot_dir, "generate_gif.js")
    
    # Map phase names
    phase_map = {
        'betting': 'betting',
        'running': 'running',
        'supersonic': 'supersonic',
        'crashed': 'crashed'
    }
    
    mapped_phase = phase_map.get(phase, 'running')
    
    try:
        # Call Node.js script to generate GIF with shorter timeout
        result = subprocess.run(
            ["node", node_script, mapped_phase, str(multiplier), output_path],
            cwd=bot_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',  # Ignore decode errors
            timeout=10  # Reduced timeout to 10 seconds
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"[GIF] Generated: {output_path}")
            return output_path
        else:
            print(f"[GIF] Node.js failed (returncode {result.returncode}), using fallback")
            return _generate_simple_gif(phase, multiplier, output_path)
        
    except subprocess.TimeoutExpired:
        print(f"[GIF] Node.js timed out, using PIL fallback")
        return _generate_simple_gif(phase, multiplier, output_path)
    except Exception as e:
        print(f"[GIF] Failed to generate with Node.js: {e}")
        return _generate_simple_gif(phase, multiplier, output_path)


def _generate_simple_gif(phase: str, multiplier: float, output_path: str) -> str:
    """Fallback: generate a nice-looking static image as GIF using PIL"""
    from PIL import Image, ImageDraw, ImageFont
    
    # Create image with transparent background
    img = Image.new('RGBA', (700, 400), (30, 31, 35, 255))  # Discord dark background
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to load a nice font
        font_large = ImageFont.truetype("arial.ttf", 120)
        font_small = ImageFont.truetype("arial.ttf", 36)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Colors based on phase
    phase_config = {
        'betting': {
            'color': (254, 231, 92),  # Yellow
            'emoji': '🎰',
            'text': 'BETTING'
        },
        'running': {
            'color': (34, 197, 94),  # Green
            'emoji': '🚀',
            'text': f'{multiplier:.2f}x'
        },
        'supersonic': {
            'color': (255, 140, 0),  # Orange
            'emoji': '🔥',
            'text': f'{multiplier:.2f}x'
        },
        'crashed': {
            'color': (220, 50, 50),  # Red
            'emoji': '💥',
            'text': f'{multiplier:.2f}x'
        }
    }
    
    config = phase_config.get(phase, phase_config['running'])
    
    # Draw main multiplier text
    main_text = config['text']
    bbox = draw.textbbox((0, 0), main_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (700 - text_width) // 2
    y = (400 - text_height) // 2
    
    # Draw shadow for depth
    draw.text((x + 3, y + 3), main_text, fill=(0, 0, 0, 180), font=font_large)
    # Draw main text
    draw.text((x, y), main_text, fill=config['color'], font=font_large)
    
    # Draw phase label at top
    label_text = f"{config['emoji']} {phase.upper()}"
    bbox2 = draw.textbbox((0, 0), label_text, font=font_small)
    label_width = bbox2[2] - bbox2[0]
    draw.text(((700 - label_width) // 2, 30), label_text, fill=(200, 200, 200), font=font_small)
    
    # Save as GIF
    img.save(output_path, 'GIF', duration=100, loop=0)
    
    print(f"[GIF] Created PIL fallback: {output_path}")
    return output_path


def generate_bet_results_image(bets: list, output_path: str = "crash_bets.png") -> str:
    """
    Generate static image showing bet results table.
    
    Args:
        bets: List of bet dictionaries with username, amount, cashed_out, cashout_multiplier
        output_path: Where to save the image
    
    Returns:
        Path to generated image file
    """
    from PIL import Image, ImageDraw, ImageFont
    
    width = 700
    row_height = 35
    header_height = 40
    padding = 20
    height = header_height + (len(bets) * row_height) + padding if bets else 100
    
    # Transparent background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to load Poppins font
    try:
        header_font = ImageFont.truetype("C:/Windows/Fonts/Poppins-SemiBold.ttf", 14)
        row_font = ImageFont.truetype("C:/Windows/Fonts/Poppins-Regular.ttf", 13)
    except:
        try:
            header_font = ImageFont.truetype("arial.ttf", 14)
            row_font = ImageFont.truetype("arial.ttf", 13)
        except:
            header_font = ImageFont.load_default()
            row_font = ImageFont.load_default()
    
    # Table header
    y = 10
    draw.text((20, y), "Player", fill=(180, 180, 180), font=header_font)
    draw.text((250, y), "Bet", fill=(180, 180, 180), font=header_font)
    draw.text((400, y), "Multiplier", fill=(180, 180, 180), font=header_font)
    draw.text((550, y), "Result", fill=(180, 180, 180), font=header_font)
    
    # Separator line
    y += 30
    draw.line([(20, y), (width - 20, y)], fill=(100, 100, 100), width=1)
    
    y += 10
    
    # Bet rows
    if not bets:
        draw.text((20, y), "No bets placed", fill=(150, 150, 150), font=row_font)
    else:
        for bet in bets:
            username = str(bet.get('username', 'Unknown'))[:18]
            amount = bet.get('amount', 0)
            cashed_out = bet.get('cashed_out', False)
            cashout_mult = bet.get('cashout_multiplier', 0)
            
            # Player name
            draw.text((20, y), username, fill=(200, 200, 200), font=row_font)
            
            # Bet amount
            draw.text((250, y), f"{amount}", fill=(200, 200, 200), font=row_font)
            
            # Result
            if cashed_out:
                # Cashed out - show multiplier and winnings
                winnings = int(amount * cashout_mult)
                draw.text((400, y), f"{cashout_mult:.2f}x", fill=(34, 197, 94), font=row_font)
                draw.text((550, y), f"+{winnings}", fill=(34, 197, 94), font=row_font)
            else:
                # Still active or lost
                draw.text((400, y), "-", fill=(150, 150, 150), font=row_font)
                draw.text((550, y), "Lost", fill=(220, 50, 50), font=row_font)
            
            y += row_height
    
    img.save(output_path, "PNG")
    return output_path
