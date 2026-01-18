from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ReasonCode(str, Enum):
    TREND_FAIL = "TREND_FAIL"
    ENTRY_CROSS = "ENTRY_CROSS"
    VOL_CONFIRM = "VOL_CONFIRM"
    BREAKOUT_CONFIRM = "BREAKOUT_CONFIRM"

    ORDER_PLACED = "ORDER_PLACED"
    LIMIT_FILLED = "LIMIT_FILLED"
    LIMIT_EXPIRED = "LIMIT_EXPIRED"

    STOP = "STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    TIME_STOP = "TIME_STOP"


@dataclass(frozen=True)
class StrategyParams:
    limit_expiry_bars: int = 4

    maker_fee_bps: float = 0.0
    taker_fee_bps: float = 0.0
    slippage_bps: float = 0.0

    atr_stop_mult: float = 1.0
    take_profit_r: float = 2.0
    time_stop_bars: int | None = None


@dataclass(frozen=True)
class EntrySignal:
    ts: int
    side: Side
    limit_px: float
    reasons: list[ReasonCode] = field(default_factory=list)


@dataclass
class LimitOrder:
    placed_ts: int
    side: Side
    limit_px: float
    expiry_bars: int
    age_bars: int = 0
    reasons: list[ReasonCode] = field(default_factory=list)

    filled: bool = False
    fill_ts: int | None = None
    fill_px: float | None = None
    expired: bool = False
