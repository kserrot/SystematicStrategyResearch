from __future__ import annotations

from dataclasses import dataclass

from src.strategies.v1.spec import ReasonCode


@dataclass(frozen=True)
class Brackets:
    stop_px: float
    tp_px: float


def compute_long_brackets(
    entry_px: float,
    atr: float,
    atr_mult: float,
    take_profit_r: float,
) -> Brackets:
    entry = float(entry_px)
    a = float(atr)

    if a <= 0:
        raise ValueError("ATR must be > 0 to compute brackets.")

    stop_px = entry - float(atr_mult) * a
    r = entry - stop_px
    tp_px = entry + float(take_profit_r) * r

    return Brackets(stop_px=stop_px, tp_px=tp_px)


def check_long_exit(
    low: float,
    high: float,
    brackets: Brackets,
) -> tuple[float | None, ReasonCode | None]:
    """
    Returns (exit_px, reason) if stop/TP hit in this bar, else (None, None).

    Conservative ordering:
      If BOTH stop and TP are touched in the same bar, assume STOP is hit first.
    """
    lo = float(low)
    hi = float(high)

    stop_hit = lo <= float(brackets.stop_px)
    tp_hit = hi >= float(brackets.tp_px)

    if stop_hit:
        return float(brackets.stop_px), ReasonCode.STOP

    if tp_hit:
        return float(brackets.tp_px), ReasonCode.TAKE_PROFIT

    return None, None
