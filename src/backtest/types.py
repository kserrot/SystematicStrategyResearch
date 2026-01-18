from __future__ import annotations

from dataclasses import dataclass

from src.strategies.v1.spec import ReasonCode, Side


@dataclass(frozen=True)
class Trade:
    symbol: str
    side: Side

    entry_ts: int
    entry_px: float

    exit_ts: int
    exit_px: float

    reasons: list[ReasonCode]
