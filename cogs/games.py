"""
cogs/games.py
Minigames & Economy Cog for Miso Bot.

Features:
- /mines [bet] [bombs] [grid] — Interactive 3x3, 4x4, or 5x5 Mines with custom emoji buttons.
- /blackjack [bet] — Interactive Blackjack 21 with visual cards & transparent card table.
- /slots [bet] — Compact 3-segment visual slot machine frame on transparent canvas.
- /coinflip [bet] [choice] — Visual Coinflip outcome card.
- /roulette [bet] [space] — Visual Roulette table game (Red/Black/Green/Number).
- /tower [bet] [difficulty] — Interactive multi-floor Tower Climber minigame.
- /richest — Paginated visual economy leaderboard.
- /balance [@user] — Check wallet balance.
- /daily — Claim daily coins with streak multiplier.
- /pay [@user] [amount] — Transfer coins to another member.
"""

import asyncio
import io
import math
import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config

# Import async Supabase economy functions
from functions import economy_supabase

# Sync wrappers using create_task for fire-and-forget (used in button callbacks)
def get_balance_sync(user_id: int) -> int:
    """Sync wrapper - blocks until result is available"""
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(economy_supabase.get_balance(user_id))

def add_balance_sync(user_id: int, amount: int) -> int:
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(economy_supabase.add_balance(user_id, amount))

def remove_balance_sync(user_id: int, amount: int) -> bool:
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(economy_supabase.remove_balance(user_id, amount))

def record_game_result_sync(user_id: int, won: bool, profit_or_loss: int) -> None:
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(economy_supabase.record_game_result(user_id, won, profit_or_loss))

# For game commands, use async versions
async def get_balance(user_id: int) -> int:
    return await economy_supabase.get_balance(user_id)

async def add_balance(user_id: int, amount: int) -> int:
    return await economy_supabase.add_balance(user_id, amount)

async def remove_balance(user_id: int, amount: int) -> bool:
    return await economy_supabase.remove_balance(user_id, amount)

async def record_game_result(user_id: int, won: bool, profit_or_loss: int) -> None:
    await economy_supabase.record_game_result(user_id, won, profit_or_loss)

async def claim_daily(user_id: int) -> tuple[bool, int, str | None]:
    return await economy_supabase.claim_daily(user_id)

async def transfer_coins(sender_id: int, receiver_id: int, amount: int) -> tuple[bool, str]:
    return await economy_supabase.transfer_coins(sender_id, receiver_id, amount)

async def get_rich_leaderboard(limit: int = 10) -> list[dict]:
    return await economy_supabase.get_rich_leaderboard(limit)

from functions.renderer import (
    render_blackjack_table,
    render_coinflip_card,
    render_leaderboard_card,
    render_mines_board,
    render_roulette_card,
    render_slots_machine,
    render_tower_board,
)


# ==========================================
# MINES HELPERS & VIEW
# ==========================================

def calculate_mines_multiplier(total_tiles: int, bombs_count: int, safe_revealed: int) -> float:
    if safe_revealed == 0:
        return 1.0
    rtp = 0.97
    comb_safe = math.comb(total_tiles - bombs_count, safe_revealed)
    comb_total = math.comb(total_tiles, safe_revealed)
    prob = comb_safe / comb_total
    multiplier = rtp / prob
    return max(1.02, round(multiplier, 2))


class MinesTileButton(discord.ui.Button):
    def __init__(self, index: int, row: int) -> None:
        super().__init__(
            label=f"{index + 1}",
            style=discord.ButtonStyle.secondary,
            row=row,
            custom_id=f"mines_tile_{index}",
        )
        self.tile_index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        view: MinesGameView = self.view  # type: ignore
        if interaction.user.id != view.player_id:
            await interaction.response.defer()
            await interaction.followup.send("This is not your Mines game!", ephemeral=True)
            return
        await view.handle_tile_click(interaction, self.tile_index)


class MinesCashoutButton(discord.ui.Button):
    def __init__(self, row: int = 4) -> None:
        super().__init__(
            label="Cash Out (+0)",
            style=discord.ButtonStyle.success,
            emoji=discord.PartialEmoji.from_str(config.EMOJI_MINES_GEM),
            row=row,
            disabled=True,
            custom_id="mines_cashout",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: MinesGameView = self.view  # type: ignore
        if interaction.user.id != view.player_id:
            await interaction.response.defer()
            await interaction.followup.send("This is not your Mines game!", ephemeral=True)
            return
        await view.handle_cashout(interaction)


class MinesGameView(discord.ui.View):
    def __init__(
        self,
        player_id: int,
        bet: int,
        bombs_count: int,
        grid_dim: int = 5,
    ) -> None:
        super().__init__(timeout=180)
        self.player_id = player_id
        self.bet = bet
        self.grid_dim = grid_dim
        self.total_tiles = grid_dim * grid_dim
        self.bombs_count = bombs_count
        self.safe_count = 0
        self.game_over = False

        self.bomb_indices = set(random.sample(range(self.total_tiles), self.bombs_count))
        self.tiles_state = ["hidden"] * self.total_tiles
        self.tile_buttons: list[MinesTileButton] = []

        if self.grid_dim == 3:
            for i in range(9):
                btn = MinesTileButton(index=i, row=i // 3)
                self.tile_buttons.append(btn)
                self.add_item(btn)
            self.cashout_btn = MinesCashoutButton(row=3)
            self.add_item(self.cashout_btn)

        elif self.grid_dim == 4:
            for i in range(16):
                btn = MinesTileButton(index=i, row=i // 4)
                self.tile_buttons.append(btn)
                self.add_item(btn)
            self.cashout_btn = MinesCashoutButton(row=4)
            self.add_item(self.cashout_btn)

        else:
            for i in range(25):
                btn = MinesTileButton(index=i, row=i // 5)
                self.tile_buttons.append(btn)
                self.add_item(btn)
            self.cashout_btn = MinesCashoutButton(row=4)
            self.remove_item(self.tile_buttons[24])
            self.add_item(self.cashout_btn)

    def current_multiplier(self) -> float:
        return calculate_mines_multiplier(self.total_tiles, self.bombs_count, self.safe_count)

    def current_payout(self) -> int:
        return int(self.bet * self.current_multiplier())

    def current_profit(self) -> int:
        return self.current_payout() - self.bet

    async def get_rendered_image_file(self) -> discord.File:
        mult_str = f"{self.current_multiplier():.2f}x"
        profit_str = f"+{self.current_profit()}" if self.safe_count > 0 else "+0"
        gems_remaining = (self.total_tiles - self.bombs_count) - self.safe_count

        png_bytes = await render_mines_board(
            tiles_state=self.tiles_state,
            gems_left=max(0, gems_remaining),
            bombs_count=self.bombs_count,
            profit_text=profit_str,
            multiplier_text=mult_str,
            grid_size=self.grid_dim,
        )
        return discord.File(io.BytesIO(png_bytes), filename="mines_board.png")

    async def handle_tile_click(self, interaction: discord.Interaction, index: int) -> None:
        if self.game_over or self.tiles_state[index] != "hidden":
            return

        if index in self.bomb_indices:
            self.game_over = True
            for i in range(self.total_tiles):
                if i in self.bomb_indices:
                    self.tiles_state[i] = "bomb"
                    if i < len(self.tile_buttons):
                        self.tile_buttons[i].emoji = discord.PartialEmoji.from_str(config.EMOJI_MINES_BOMB)
                        self.tile_buttons[i].label = None
                        self.tile_buttons[i].style = discord.ButtonStyle.danger
                elif self.tiles_state[i] == "hidden":
                    self.tiles_state[i] = "gem"

            for item in self.children:
                item.disabled = True

            await record_game_result(self.player_id, won=False, profit_or_loss=-self.bet)

            await interaction.response.defer()
            file = await self.get_rendered_image_file()

            embed = discord.Embed(
                title=f"{config.EMOJI_MINES_BOMB} Game Over — You hit a Mine!",
                description=(
                    f"You stepped on a mine at tile **#{index + 1}**.\n"
                    f"You lost **{self.bet}** {config.EMOJI_COIN} coins."
                ),
                color=config.COLOR_ERROR,
            )
            embed.set_image(url="attachment://mines_board.png")
            embed.set_footer(text=f"Better luck next time! • Bet: {self.bet}")

            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self,
                attachments=[file],
            )
            return

        self.tiles_state[index] = "gem"
        self.safe_count += 1

        if index < len(self.tile_buttons):
            btn = self.tile_buttons[index]
            btn.disabled = True
            btn.style = discord.ButtonStyle.success
            btn.emoji = discord.PartialEmoji.from_str(config.EMOJI_MINES_GEM)
            btn.label = None

        max_safe = self.total_tiles - self.bombs_count
        if self.safe_count >= max_safe:
            await self.handle_cashout(interaction, max_win=True)
            return

        profit = self.current_profit()
        self.cashout_btn.disabled = False
        self.cashout_btn.label = f"Cash Out (+{profit})"

        await interaction.response.defer()
        file = await self.get_rendered_image_file()

        embed = discord.Embed(
            title=f"{config.EMOJI_MINES_GEM} Mines — Active Round",
            description=(
                f"Gems found: **{self.safe_count}/{max_safe}**\n"
                f"Current Payout: **{self.current_payout()}** {config.EMOJI_COIN} "
                f"(`{self.current_multiplier():.2f}x` | **+{profit}**)"
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_image(url="attachment://mines_board.png")
        embed.set_footer(text=f"Click another tile or Cash Out! • Bet: {self.bet}")

        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self,
            attachments=[file],
        )

    async def handle_cashout(self, interaction: discord.Interaction, max_win: bool = False) -> None:
        if self.game_over:
            return
        self.game_over = True

        payout = self.current_payout()
        profit = self.current_profit()
        await add_balance(self.player_id, payout)
        await record_game_result(self.player_id, won=True, profit_or_loss=profit)

        for i in range(self.total_tiles):
            if i in self.bomb_indices:
                self.tiles_state[i] = "bomb"
            elif self.tiles_state[i] == "hidden":
                self.tiles_state[i] = "gem"

        for item in self.children:
            item.disabled = True

        if not interaction.response.is_done():
            await interaction.response.defer()

        file = await self.get_rendered_image_file()

        title_text = "🎉 MAX WIN! Board Cleared!" if max_win else f"💎 Cashed Out (+{profit} coins)!"
        embed = discord.Embed(
            title=title_text,
            description=(
                f"Successfully cashed out at **{self.current_multiplier():.2f}x**!\n"
                f"**Total Payout:** `{payout}` {config.EMOJI_COIN}\n"
                f"**Net Profit:** `+{profit}` {config.EMOJI_COIN}"
            ),
            color=config.COLOR_SUCCESS,
        )
        embed.set_image(url="attachment://mines_board.png")
        embed.set_footer(text=f"Gems Found: {self.safe_count} • Total Bet: {self.bet}")

        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self,
            attachments=[file],
        )


# ==========================================
# BLACKJACK ENGINE & VIEW
# ==========================================

SUITS = [("♠", False), ("♥", True), ("♦", True), ("♣", False)]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


def _draw_card() -> dict:
    rank = random.choice(RANKS)
    suit, is_red = random.choice(SUITS)
    return {"rank": rank, "suit": suit, "is_red": is_red, "hidden": False}


def _calc_hand_score(cards: list[dict], hide_second: bool = False) -> tuple[int, str]:
    if hide_second and len(cards) >= 2:
        val = 11 if cards[0]["rank"] == "A" else (10 if cards[0]["rank"] in ["J", "Q", "K"] else int(cards[0]["rank"]))
        return val, f"{val} + ?"

    total = 0
    aces = 0
    for c in cards:
        r = c["rank"]
        if r == "A":
            aces += 1
            total += 11
        elif r in ["K", "Q", "J"]:
            total += 10
        else:
            total += int(r)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total, str(total)


class BlackjackView(discord.ui.View):
    def __init__(self, player_id: int, bet: int) -> None:
        super().__init__(timeout=120)
        self.player_id = player_id
        self.bet = bet
        self.player_cards = [_draw_card(), _draw_card()]
        self.dealer_cards = [_draw_card(), _draw_card()]
        self.game_over = False

    async def get_rendered_table(self, hide_dealer: bool = True) -> discord.File:
        d_cards = [self.dealer_cards[0], {"hidden": True}] if hide_dealer else self.dealer_cards
        _, d_score_str = _calc_hand_score(self.dealer_cards, hide_second=hide_dealer)
        _, p_score_str = _calc_hand_score(self.player_cards)

        png_bytes = await render_blackjack_table(
            dealer_cards=d_cards,
            dealer_score=d_score_str,
            player_cards=self.player_cards,
            player_score=p_score_str,
        )
        return discord.File(io.BytesIO(png_bytes), filename="blackjack.png")

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="🃏")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.player_id:
            await interaction.response.defer()
            await interaction.followup.send("This is not your game!", ephemeral=True)
            return

        self.player_cards.append(_draw_card())
        p_score, _ = _calc_hand_score(self.player_cards)

        if p_score > 21:
            await self.end_game(interaction, "bust")
        elif p_score == 21:
            await self.stand_callback(interaction)
        else:
            await interaction.response.defer()
            file = await self.get_rendered_table(hide_dealer=True)
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                attachments=[file],
                view=self,
            )

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.player_id:
            await interaction.response.defer()
            await interaction.followup.send("This is not your game!", ephemeral=True)
            return
        await self.stand_callback(interaction)

    async def stand_callback(self, interaction: discord.Interaction) -> None:
        p_score, _ = _calc_hand_score(self.player_cards)

        d_score, _ = _calc_hand_score(self.dealer_cards)
        while d_score < 17:
            self.dealer_cards.append(_draw_card())
            d_score, _ = _calc_hand_score(self.dealer_cards)

        if d_score > 21:
            await self.end_game(interaction, "dealer_bust")
        elif p_score > d_score:
            await self.end_game(interaction, "win")
        elif p_score < d_score:
            await self.end_game(interaction, "lose")
        else:
            await self.end_game(interaction, "push")

    async def end_game(self, interaction: discord.Interaction, outcome: str) -> None:
        self.game_over = True
        for item in self.children:
            item.disabled = True

        p_score, _ = _calc_hand_score(self.player_cards)
        d_score, _ = _calc_hand_score(self.dealer_cards)

        if outcome in ["win", "dealer_bust"]:
            payout = self.bet * 2
            profit = self.bet
            await add_balance(self.player_id, payout)
            await record_game_result(self.player_id, won=True, profit_or_loss=profit)
            desc = f"🎉 **You Won!** +{payout} {config.EMOJI_COIN} (`+{profit}` profit)\nYour: `{p_score}` vs Dealer: `{d_score}`"
            color = config.COLOR_SUCCESS
        elif outcome == "push":
            await add_balance(self.player_id, self.bet)
            desc = f"🤝 **Push (Tie)!** Your `{self.bet}` {config.EMOJI_COIN} was returned.\nBoth scored `{p_score}`."
            color = config.COLOR_WARNING
        else:
            await record_game_result(self.player_id, won=False, profit_or_loss=-self.bet)
            desc = f"💥 **You Lost!** -{self.bet} {config.EMOJI_COIN}\nYour: `{p_score}` vs Dealer: `{d_score}`"
            color = config.COLOR_ERROR

        if not interaction.response.is_done():
            await interaction.response.defer()

        file = await self.get_rendered_table(hide_dealer=False)
        embed = discord.Embed(
            title="♠️ Blackjack 21",
            description=desc,
            color=color,
        )
        embed.set_image(url="attachment://blackjack.png")
        embed.set_footer(text=f"Bet: {self.bet} • Balance: {get_balance_sync(self.player_id)}")

        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self,
            attachments=[file],
        )


# ==========================================
# TOWER CLIMBER ENGINE & VIEW
# ==========================================

TOWER_MULTIPLIERS_EASY = [1.35, 1.85, 2.50, 3.40, 4.60, 6.20, 8.50, 12.00]  # 1 skull out of 3
TOWER_MULTIPLIERS_HARD = [1.90, 3.80, 7.60, 15.00, 30.00, 60.00, 120.00, 250.00]  # 2 skulls out of 3


class TowerClimberView(discord.ui.View):
    def __init__(self, player_id: int, bet: int, is_hard: bool = False) -> None:
        super().__init__(timeout=120)
        self.player_id = player_id
        self.bet = bet
        self.is_hard = is_hard
        self.current_floor = 0  # 0 to 7
        self.game_over = False

        self.multipliers = TOWER_MULTIPLIERS_HARD if is_hard else TOWER_MULTIPLIERS_EASY
        self.skulls_per_floor = 2 if is_hard else 1

        # Pre-generate skull positions for 8 floors (each floor has 3 tiles)
        self.skull_positions = []
        for _ in range(8):
            skulls = set(random.sample(range(3), self.skulls_per_floor))
            self.skull_positions.append(skulls)

        self.floors_state = [["hidden", "hidden", "hidden"] for _ in range(8)]

        self.add_control_buttons()

    def add_control_buttons(self) -> None:
        self.clear_items()
        # Row 0: 3 pick buttons
        for i, label in enumerate(["Left", "Middle", "Right"]):
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, row=0, custom_id=f"tower_tile_{i}")
            btn.callback = self.make_pick_callback(i)
            self.add_item(btn)

        # Row 1: Cashout
        profit = self.current_profit()
        cashout_btn = discord.ui.Button(
            label=f"Cash Out (+{profit})",
            style=discord.ButtonStyle.success,
            emoji=discord.PartialEmoji.from_str(config.EMOJI_MINES_GEM),
            row=1,
            disabled=self.current_floor == 0,
            custom_id="tower_cashout",
        )
        cashout_btn.callback = self.cashout_callback
        self.add_item(cashout_btn)

    def current_multiplier(self) -> float:
        if self.current_floor == 0:
            return 1.0
        return self.multipliers[self.current_floor - 1]

    def current_payout(self) -> int:
        return int(self.bet * self.current_multiplier())

    def current_profit(self) -> int:
        return self.current_payout() - self.bet

    async def get_rendered_board(self) -> discord.File:
        mult_str = f"{self.current_multiplier():.2f}x"
        profit_str = f"+{self.current_profit()}" if self.current_floor > 0 else "+0"

        png_bytes = await render_tower_board(
            floors_data=self.floors_state,
            current_floor=self.current_floor,
            multiplier_text=mult_str,
            profit_text=profit_str,
        )
        return discord.File(io.BytesIO(png_bytes), filename="tower_board.png")

    def make_pick_callback(self, tile_index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player_id:
                await interaction.response.defer()
                await interaction.followup.send("This is not your Tower game!", ephemeral=True)
                return
            await self.handle_pick(interaction, tile_index)
        return callback

    async def handle_pick(self, interaction: discord.Interaction, pick_idx: int) -> None:
        if self.game_over:
            return

        floor = self.current_floor
        skulls = self.skull_positions[floor]

        # 1. HIT SKULL -> LOSE
        if pick_idx in skulls:
            self.game_over = True
            for i in range(3):
                self.floors_state[floor][i] = "skull" if i in skulls else "safe"

            for item in self.children:
                item.disabled = True

            await record_game_result(self.player_id, won=False, profit_or_loss=-self.bet)

            await interaction.response.defer()
            file = await self.get_rendered_board()

            embed = discord.Embed(
                title=f"{config.EMOJI_MINES_BOMB} Tower Climber — Fallen!",
                description=f"You stepped on a skull at **Floor {floor + 1}**.\nYou lost **{self.bet}** {config.EMOJI_COIN} coins.",
                color=config.COLOR_ERROR,
            )
            embed.set_image(url="attachment://tower_board.png")
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self,
                attachments=[file],
            )
            return

        # 2. SAFE TILE
        for i in range(3):
            self.floors_state[floor][i] = "skull" if i in skulls else "safe"

        self.current_floor += 1

        # Reached the top floor (Floor 8 cleared!)
        if self.current_floor >= 8:
            await self.handle_cashout(interaction, max_win=True)
            return

        self.add_control_buttons()
        await interaction.response.defer()
        file = await self.get_rendered_board()

        profit = self.current_profit()
        embed = discord.Embed(
            title=f"🏰 Tower Climber — Floor {self.current_floor + 1}/8",
            description=(
                f"Current Payout: **{self.current_payout()}** {config.EMOJI_COIN} "
                f"(`{self.current_multiplier():.2f}x` | **+{profit}**)\n"
                f"Pick a tile on Floor {self.current_floor + 1} or Cash Out!"
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_image(url="attachment://tower_board.png")
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self,
            attachments=[file],
        )

    async def cashout_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.player_id:
            await interaction.response.defer()
            await interaction.followup.send("This is not your Tower game!", ephemeral=True)
            return
        await self.handle_cashout(interaction)

    async def handle_cashout(self, interaction: discord.Interaction, max_win: bool = False) -> None:
        if self.game_over or self.current_floor == 0:
            return
        self.game_over = True

        payout = self.current_payout()
        profit = self.current_profit()
        await add_balance(self.player_id, payout)
        await record_game_result(self.player_id, won=True, profit_or_loss=profit)

        for item in self.children:
            item.disabled = True

        if not interaction.response.is_done():
            await interaction.response.defer()

        file = await self.get_rendered_board()
        title_str = "🎉 TOWER SUMMIT CLEARED! 🏰" if max_win else f"💎 Cashed Out (+{profit} coins)!"

        embed = discord.Embed(
            title=title_str,
            description=(
                f"Successfully reached **Floor {self.current_floor}** at **{self.current_multiplier():.2f}x**!\n"
                f"**Total Payout:** `{payout}` {config.EMOJI_COIN} (**+{profit}** profit)"
            ),
            color=config.COLOR_SUCCESS,
        )
        embed.set_image(url="attachment://tower_board.png")
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self,
            attachments=[file],
        )


# ==========================================
# PAGINATED LEADERBOARD VIEW
# ==========================================

class LeaderboardPaginationView(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        all_data: list[dict],
        title: str,
        value_formatter,
        user_id: int,
        per_page: int = 5,
    ) -> None:
        super().__init__(timeout=120)
        self.bot = bot
        self.all_data = all_data
        self.title = title
        self.value_formatter = value_formatter
        self.user_id = user_id
        self.per_page = per_page
        self.current_page = 1
        self.total_pages = max(1, math.ceil(len(all_data) / per_page))

        self.update_buttons()

    def update_buttons(self) -> None:
        self.clear_items()

        prev_btn = discord.ui.Button(
            label="◀",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page <= 1,
            custom_id="lb_prev",
        )
        prev_btn.callback = self.prev_page
        self.add_item(prev_btn)

        indicator = discord.ui.Button(
            label=f"Page {self.current_page} / {self.total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            custom_id="lb_indicator",
        )
        self.add_item(indicator)

        next_btn = discord.ui.Button(
            label="▶",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page >= self.total_pages,
            custom_id="lb_next",
        )
        next_btn.callback = self.next_page
        self.add_item(next_btn)

    async def get_rendered_page_file(self) -> discord.File:
        start = (self.current_page - 1) * self.per_page
        end = start + self.per_page
        page_entries = self.all_data[start:end]

        formatted_entries = []
        for i, item in enumerate(page_entries):
            rank = start + i + 1
            uid = item.get("user_id", 0)
            user = self.bot.get_user(uid)
            if user is None and uid:
                try:
                    user = await self.bot.fetch_user(uid)
                except Exception:
                    user = None
            name = user.name if user else f"Unknown ({uid})"
            avatar_url = user.display_avatar.url if user else "https://cdn.discordapp.com/embed/avatars/0.png"
            val_str = self.value_formatter(item)
            formatted_entries.append({
                "rank": rank,
                "avatar_url": avatar_url,
                "name": name,
                "value_str": val_str,
            })

        png_bytes = await render_leaderboard_card(
            title=self.title,
            entries=formatted_entries,
            page=self.current_page,
            total_pages=self.total_pages,
        )
        return discord.File(io.BytesIO(png_bytes), filename="leaderboard.png")

    async def prev_page(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            await interaction.followup.send("This is not your menu!", ephemeral=True)
            return
        if self.current_page > 1:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.defer()
            file = await self.get_rendered_page_file()
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                attachments=[file],
                view=self,
            )

    async def next_page(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your menu!", ephemeral=True)
            return
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.defer()
            file = await self.get_rendered_page_file()
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                attachments=[file],
                view=self,
            )


# ==========================================
# GAMES COG CLASS
# ==========================================

class Games(commands.Cog):
    """Minigames & Economy commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ==========================================
    # /MINES
    # ==========================================
    @app_commands.command(name="mines", description="Play interactive Mines to find gems and avoid bombs!")
    @app_commands.describe(
        bet="Amount of coins to bet (minimum 10)",
        bombs="Number of mines on the board",
        grid="Grid size (3x3, 4x4, or 5x5)",
    )
    @app_commands.choices(
        grid=[
            app_commands.Choice(name="5x5 (25 Tiles)", value="5"),
            app_commands.Choice(name="4x4 (16 Tiles)", value="4"),
            app_commands.Choice(name="3x3 (9 Tiles)", value="3"),
        ]
    )
    async def mines(
        self,
        interaction: discord.Interaction,
        bet: int = 50,
        bombs: int = 3,
        grid: app_commands.Choice[str] = None,
    ) -> None:
        grid_size = int(grid.value) if grid else 5
        total_tiles = grid_size * grid_size

        if bet < 10:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Minimum bet is **10** {config.EMOJI_COIN} coins.",
                ephemeral=True,
            )
            return

        if not (1 <= bombs < total_tiles):
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Bombs count must be between **1 and {total_tiles - 1}**.",
                ephemeral=True,
            )
            return

        user_balance = await get_balance(interaction.user.id)
        if user_balance < bet:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} You don't have enough coins! Balance: **{user_balance}** {config.EMOJI_COIN}",
                ephemeral=True,
            )
            return

        await remove_balance(interaction.user.id, bet)

        game_view = MinesGameView(
            player_id=interaction.user.id,
            bet=bet,
            bombs_count=bombs,
            grid_dim=grid_size,
        )

        await interaction.response.defer()
        file = await game_view.get_rendered_image_file()

        embed = discord.Embed(
            title=f"{config.EMOJI_MINES_GEM} Mines ({grid_size}x{grid_size} • {bombs} Mines)",
            description=(
                f"**Bet:** `{bet}` {config.EMOJI_COIN}\n"
                f"Click any numbered tile below to reveal a safe gem!\n"
                f"Cash out anytime to bank your winnings."
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_image(url="attachment://mines_board.png")
        embed.set_footer(text=f"{config.BOT_NAME} Minigames • {total_tiles} Tiles")

        await interaction.followup.send(embed=embed, view=game_view, file=file)

    # ==========================================
    # /BLACKJACK
    # ==========================================
    @app_commands.command(name="blackjack", description="Play Blackjack 21 against the house!")
    @app_commands.describe(bet="Amount of coins to bet (minimum 10)")
    async def blackjack(self, interaction: discord.Interaction, bet: int = 50) -> None:
        if bet < 10:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Minimum bet is **10** {config.EMOJI_COIN} coins.",
                ephemeral=True,
            )
            return

        balance = await get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Insufficient balance! You have **{balance}** {config.EMOJI_COIN}",
                ephemeral=True,
            )
            return

        await remove_balance(interaction.user.id, bet)

        bj_view = BlackjackView(player_id=interaction.user.id, bet=bet)
        await interaction.response.defer()

        p_score, _ = _calc_hand_score(bj_view.player_cards)
        if p_score == 21:
            payout = int(bet * 2.5)
            profit = payout - bet
            await add_balance(interaction.user.id, payout)
            await record_game_result(interaction.user.id, won=True, profit_or_loss=profit)

            file = await bj_view.get_rendered_table(hide_dealer=False)
            embed = discord.Embed(
                title="♠️ Natural Blackjack 21! 🎉",
                description=f"**Instant Win!** Won `{payout}` {config.EMOJI_COIN} (`+{profit}` profit)",
                color=config.COLOR_SUCCESS,
            )
            embed.set_image(url="attachment://blackjack.png")
            await interaction.followup.send(embed=embed, file=file)
            return

        file = await bj_view.get_rendered_table(hide_dealer=True)
        embed = discord.Embed(
            title="♠️ Blackjack 21",
            description=f"**Bet:** `{bet}` {config.EMOJI_COIN}\nHit for another card or Stand to hold your hand.",
            color=config.COLOR_PRIMARY,
        )
        embed.set_image(url="attachment://blackjack.png")
        embed.set_footer(text=f"{config.BOT_NAME} Minigames")

        await interaction.followup.send(embed=embed, view=bj_view, file=file)

    # ==========================================
    # /TOWER CLIMBER
    # ==========================================
    @app_commands.command(name="tower", description="Climb the multi-floor tower for huge multipliers!")
    @app_commands.describe(
        bet="Amount of coins to bet (minimum 10)",
        difficulty="Difficulty mode (Easy = 1 skull per floor, Hard = 2 skulls)",
    )
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name="Easy (2 Gems / 1 Skull)", value="easy"),
            app_commands.Choice(name="Hard (1 Gem / 2 Skulls - Big Payouts)", value="hard"),
        ]
    )
    async def tower(
        self,
        interaction: discord.Interaction,
        bet: int = 50,
        difficulty: app_commands.Choice[str] = None,
    ) -> None:
        if bet < 10:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Minimum bet is **10** {config.EMOJI_COIN} coins.",
                ephemeral=True,
            )
            return

        balance = await get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Insufficient balance! You have **{balance}** {config.EMOJI_COIN}",
                ephemeral=True,
            )
            return

        await remove_balance(interaction.user.id, bet)
        is_hard = (difficulty.value == "hard") if difficulty else False

        tower_view = TowerClimberView(player_id=interaction.user.id, bet=bet, is_hard=is_hard)
        await interaction.response.defer()
        file = await tower_view.get_rendered_board()

        embed = discord.Embed(
            title=f"🏰 Tower Climber ({'Hard' if is_hard else 'Easy'} Mode)",
            description=(
                f"**Bet:** `{bet}` {config.EMOJI_COIN}\n"
                f"Pick **Left**, **Middle**, or **Right** to climb to Floor 1!\n"
                f"Cash out anytime to bank your earnings."
            ),
            color=config.COLOR_PRIMARY,
        )
        embed.set_image(url="attachment://tower_board.png")
        embed.set_footer(text=f"{config.BOT_NAME} Minigames • 8 Floors")

        await interaction.followup.send(embed=embed, view=tower_view, file=file)

    # ==========================================
    # /ROULETTE
    # ==========================================
    @app_commands.command(name="roulette", description="Place a bet on the European roulette wheel!")
    @app_commands.describe(
        bet="Amount of coins to bet (minimum 10)",
        space="Bet on Red (2x), Black (2x), Green (14x), or a specific number 0-36 (36x)",
    )
    async def roulette(
        self,
        interaction: discord.Interaction,
        bet: int,
        space: str,
    ) -> None:
        await interaction.response.defer()
        
        if bet < 10:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Minimum bet is **10** {config.EMOJI_COIN} coins.",
                ephemeral=True,
            )
            return

        balance = await get_balance(interaction.user.id)
        if balance < bet:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Insufficient balance! You have **{balance}** {config.EMOJI_COIN}",
                ephemeral=True,
            )
            return

        space_clean = space.strip().lower()
        valid_spaces = ["red", "black", "green"]
        is_num = space_clean.isdigit() and (0 <= int(space_clean) <= 36)

        if space_clean not in valid_spaces and not is_num:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Invalid space! Choose `red`, `black`, `green`, or a number `0-36`.",
                ephemeral=True,
            )
            return

        await remove_balance(interaction.user.id, bet)

        # Spin wheel (0 to 36)
        landed_number = random.randint(0, 36)
        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

        if landed_number == 0:
            landed_color = "green"
        elif landed_number in red_numbers:
            landed_color = "red"
        else:
            landed_color = "black"

        won = False
        mult = 0.0

        if is_num and int(space_clean) == landed_number:
            won = True
            mult = 36.0
        elif space_clean == "green" and landed_number == 0:
            won = True
            mult = 14.0
        elif space_clean in ["red", "black"] and space_clean == landed_color:
            won = True
            mult = 2.0

        payout = int(bet * mult)
        profit = payout - bet

        if won:
            await add_balance(interaction.user.id, payout)
            await record_game_result(interaction.user.id, won=True, profit_or_loss=profit)
            payout_text = f"🎉 WON +{payout} coins (+{profit})"
            color = config.COLOR_SUCCESS
        else:
            await record_game_result(interaction.user.id, won=False, profit_or_loss=-bet)
            payout_text = f"💥 LOST -{bet} coins"
            color = config.COLOR_ERROR

        await interaction.response.defer()
        png_bytes = await render_roulette_card(landed_number, landed_color, won, payout_text)
        file = discord.File(io.BytesIO(png_bytes), filename="roulette.png")

        new_balance = await get_balance(interaction.user.id)
        embed = discord.Embed(
            title="🎡 European Roulette",
            description=f"**Bet:** `{bet}` {config.EMOJI_COIN} on **{space.upper()}**\n**New Balance:** `{new_balance:,}` {config.EMOJI_COIN}",
            color=color,
        )
        embed.set_image(url="attachment://roulette.png")
        embed.set_footer(text=f"{config.BOT_NAME} Minigames")

        await interaction.followup.send(embed=embed, file=file)

    # ==========================================
    # /SLOTS
    # ==========================================
    @app_commands.command(name="slots", description="Spin the 3-reel slot machine frame!")
    @app_commands.describe(bet="Amount of coins to bet (minimum 10)")
    async def slots(self, interaction: discord.Interaction, bet: int = 25) -> None:
        await interaction.response.defer()
        
        if bet < 10:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Minimum bet is **10** {config.EMOJI_COIN} coins.",
                ephemeral=True,
            )
            return

        balance = await get_balance(interaction.user.id)
        if balance < bet:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Insufficient balance! You have **{balance}** {config.EMOJI_COIN}",
                ephemeral=True,
            )
            return

        await remove_balance(interaction.user.id, bet)

        symbols = ["💎", "🍒", "🍋", "7️⃣", "🔔", "⭐"]
        weights = [15, 25, 25, 5, 15, 15]
        reels = random.choices(symbols, weights=weights, k=3)

        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                multiplier = 10.0
            elif reels[0] == "💎":
                multiplier = 5.0
            else:
                multiplier = 3.0
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            multiplier = 1.5
        else:
            multiplier = 0.0

        won = multiplier > 0.0
        payout = int(bet * multiplier)
        profit = payout - bet

        if won:
            await add_balance(interaction.user.id, payout)
            await record_game_result(interaction.user.id, won=True, profit_or_loss=profit)
            desc = f"🎉 **You Won!** `{payout}` {config.EMOJI_COIN} (`+{profit}` profit)"
            color = config.COLOR_SUCCESS
        else:
            await record_game_result(interaction.user.id, won=False, profit_or_loss=-bet)
            desc = f"💥 **You Lost!** -{bet} {config.EMOJI_COIN}"
            color = config.COLOR_ERROR

        await interaction.response.defer()
        png_bytes = await render_slots_machine(reels)
        file = discord.File(io.BytesIO(png_bytes), filename="slots.png")

        new_balance = await get_balance(interaction.user.id)
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"{desc}\n**Balance:** `{new_balance:,}` {config.EMOJI_COIN}",
            color=color,
        )
        embed.set_image(url="attachment://slots.png")
        embed.set_footer(text=f"Bet: {bet} • {config.BOT_NAME} Minigames")

        await interaction.followup.send(embed=embed, file=file)

    # ==========================================
    # /COINFLIP (VISUAL CARD)
    # ==========================================
    @app_commands.command(name="coinflip", description="Flip a coin against the house with visual card!")
    @app_commands.describe(bet="Amount of coins to bet", choice="Heads or Tails")
    @app_commands.choices(
        choice=[
            app_commands.Choice(name="Heads", value="heads"),
            app_commands.Choice(name="Tails", value="tails"),
        ]
    )
    async def coinflip(
        self,
        interaction: discord.Interaction,
        bet: int,
        choice: app_commands.Choice[str],
    ) -> None:
        if bet < 10:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Minimum bet is **10** {config.EMOJI_COIN} coins.",
                ephemeral=True,
            )
            return

        balance = await get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Insufficient balance! You have **{balance}** {config.EMOJI_COIN}",
                ephemeral=True,
            )
            return

        await remove_balance(interaction.user.id, bet)
        outcome = random.choice(["heads", "tails"])
        won = outcome == choice.value
        payout = bet * 2 if won else 0
        profit = bet if won else -bet

        if won:
            await add_balance(interaction.user.id, payout)
            await record_game_result(interaction.user.id, won=True, profit_or_loss=profit)
            desc = f"🎉 **You Won!** +{payout} {config.EMOJI_COIN} (`+{bet}` profit)"
            color = config.COLOR_SUCCESS
        else:
            await record_game_result(interaction.user.id, won=False, profit_or_loss=-bet)
            desc = f"💥 **You Lost!** -{bet} {config.EMOJI_COIN}"
            color = config.COLOR_ERROR

        await interaction.response.defer()
        png_bytes = await render_coinflip_card(outcome, won, bet, payout)
        file = discord.File(io.BytesIO(png_bytes), filename="coinflip.png")

        new_balance = await get_balance(interaction.user.id)
        embed = discord.Embed(
            title=f"{config.EMOJI_COIN} Coinflip ({choice.name})",
            description=f"{desc}\n**Balance:** `{new_balance:,}` {config.EMOJI_COIN}",
            color=color,
        )
        embed.set_image(url="attachment://coinflip.png")
        embed.set_footer(text=f"{config.BOT_NAME} Minigames")

        await interaction.followup.send(embed=embed, file=file)

    # ==========================================
    # /RICHEST (PAGINATED VISUAL LEADERBOARD)
    # ==========================================
    @app_commands.command(name="richest", description="View the visual coin leaderboard with interactive pages.")
    async def richest(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        leaderboard_data = await get_rich_leaderboard(limit=50)
        if not leaderboard_data:
            await interaction.followup.send(
                "*No economy records found yet. Run `/daily` to get started!*",
                ephemeral=True,
            )
            return

        def formatter(item):
            return f"{item.get('wallet', 0):,} Coins"

        view = LeaderboardPaginationView(
            bot=self.bot,
            all_data=leaderboard_data,
            title="💰 Economy Leaderboard",
            value_formatter=formatter,
            user_id=interaction.user.id,
            per_page=5,
        )

        await interaction.response.defer()
        file = await view.get_rendered_page_file()
        await interaction.followup.send(file=file, view=view)

    # ==========================================
    # /BALANCE
    # ==========================================
    @app_commands.command(name="balance", description="Check your or another user's coin balance.")
    @app_commands.describe(user="The user to check balance for (defaults to yourself)")
    async def balance(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
    ) -> None:
        target = user or interaction.user
        bal = await get_balance(target.id)

        embed = discord.Embed(
            title=f"{config.EMOJI_COIN} Coin Balance",
            description=f"**<@{target.id}>** has **{bal:,}** {config.EMOJI_COIN} coins.",
            color=config.COLOR_PRIMARY,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"{config.BOT_NAME} Economy • Use /daily for free coins")
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

    # ==========================================
    # /DAILY
    # ==========================================
    @app_commands.command(name="daily", description="Claim your daily coins reward and build your streak!")
    async def daily(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        success, amount, msg = await claim_daily(interaction.user.id)

        if success:
            new_bal = await get_balance(interaction.user.id)
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                description=(
                    f"You received **+{amount}** {config.EMOJI_COIN} coins!\n"
                    f"{config.EMOJI_CHEVRON_RIGHT} {msg}\n"
                    f"{config.EMOJI_DOTSTAR} New Balance: **{new_bal:,}** {config.EMOJI_COIN}"
                ),
                color=config.COLOR_SUCCESS,
            )
        else:
            embed = discord.Embed(
                title="⏳ Daily Already Claimed",
                description=f"You can claim your next daily reward in **{msg}**.",
                color=config.COLOR_WARNING,
            )

        embed.set_footer(text=f"{config.BOT_NAME} Daily Rewards")
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)

    # ==========================================
    # /PAY
    # ==========================================
    @app_commands.command(name="pay", description="Transfer coins to another server member.")
    @app_commands.describe(user="The member to send coins to", amount="Amount of coins to transfer")
    async def pay(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int,
    ) -> None:
        success, message = await transfer_coins(interaction.user.id, user.id, amount)
        if success:
            new_balance = await get_balance(interaction.user.id)
            embed = discord.Embed(
                description=(
                    f"{config.EMOJI_TICK} Successfully sent **{amount:,}** {config.EMOJI_COIN} "
                    f"to **<@{user.id}>**!\n"
                    f"Your New Balance: **{new_balance:,}** {config.EMOJI_COIN}"
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.defer()
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"{config.EMOJI_CROSS} {message}",
                color=config.COLOR_ERROR,
            )
            await interaction.response.defer()
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ==========================================
    # ADMIN COMMANDS
    # ==========================================
    @app_commands.command(name="give", description="[ADMIN] Give coins to a user.")
    @app_commands.describe(user="The user to give coins to", amount="Amount of coins to give")
    @app_commands.checks.has_permissions(administrator=True)
    async def give(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int,
    ) -> None:
        if amount <= 0:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Amount must be positive!",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        new_balance = await add_balance(user.id, amount)
        embed = discord.Embed(
            description=(
                f"{config.EMOJI_TICK} Gave **{amount:,}** {config.EMOJI_COIN} to **<@{user.id}>**\n"
                f"Their New Balance: **{new_balance:,}** {config.EMOJI_COIN}"
            ),
            color=config.COLOR_SUCCESS,
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="take", description="[ADMIN] Take coins from a user.")
    @app_commands.describe(user="The user to take coins from", amount="Amount of coins to take")
    @app_commands.checks.has_permissions(administrator=True)
    async def take(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int,
    ) -> None:
        if amount <= 0:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Amount must be positive!",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        current_balance = await get_balance(user.id)
        if current_balance < amount:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} User only has **{current_balance:,}** {config.EMOJI_COIN} coins!",
                ephemeral=True,
            )
            return

        success = await remove_balance(user.id, amount)
        if success:
            new_balance = await get_balance(user.id)
            embed = discord.Embed(
                description=(
                    f"{config.EMOJI_TICK} Took **{amount:,}** {config.EMOJI_COIN} from **<@{user.id}>**\n"
                    f"Their New Balance: **{new_balance:,}** {config.EMOJI_COIN}"
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Failed to take coins.",
                ephemeral=True,
            )

    @app_commands.command(name="setcoins", description="[ADMIN] Set a user's coin balance to a specific amount.")
    @app_commands.describe(user="The user to set coins for", amount="New coin balance")
    @app_commands.checks.has_permissions(administrator=True)
    async def setcoins(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int,
    ) -> None:
        if amount < 0:
            await interaction.response.defer()
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Amount cannot be negative!",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        current_balance = await get_balance(user.id)
        
        # Use set_balance from economy_supabase
        from functions.economy_supabase import set_balance
        success = await set_balance(user.id, amount)
        
        if success:
            embed = discord.Embed(
                description=(
                    f"{config.EMOJI_TICK} Set **<@{user.id}>**'s balance to **{amount:,}** {config.EMOJI_COIN}\n"
                    f"Previous Balance: **{current_balance:,}** {config.EMOJI_COIN}"
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                f"{config.EMOJI_CROSS} Failed to set balance.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Games(bot))
