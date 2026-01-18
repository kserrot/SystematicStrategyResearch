from __future__ import annotations

from dataclasses import dataclass

from src.strategies.v1.spec import ReasonCode


@dataclass(frozen=True)
class TrendResult:
    ok: bool
    reason: ReasonCode | None


def trend_ok(ema50_1h: float, ema200_1h: float) -> TrendResult:
    """
    v1 trend filter:
      EMA50_1h > EMA200_1h  => OK
      else => FAIL
    """
    if float(ema50_1h) > float(ema200_1h):
        return TrendResult(ok=True, reason=None)

    return TrendResult(ok=False, reason=ReasonCode.TREND_FAIL)
