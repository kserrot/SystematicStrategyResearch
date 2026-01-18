from __future__ import annotations

from dataclasses import dataclass

from src.strategies.v1.spec import EntrySignal, ReasonCode, Side


@dataclass(frozen=True)
class EntryRuleParams:
    """
    v1 entry rules:
      - close crosses above vwap (10m)
      - optional confirmation: vol_ratio >= min_vol_ratio
      - limit price rule: limit_px = vwap_current (simple + stable)
    """
    min_vol_ratio: float | None = None


def crosses_above(prev_close: float, prev_vwap: float, close: float, vwap: float) -> bool:
    return float(prev_close) <= float(prev_vwap) and float(close) > float(vwap)


def build_entry_signal(
    ts: int,
    prev_close: float,
    prev_vwap: float,
    close: float,
    vwap: float,
    side: Side = Side.LONG,
    vol_ratio: float | None = None,
    params: EntryRuleParams | None = None,
) -> EntrySignal | None:
    """
    Returns EntrySignal if entry conditions met, else None.
    """
    params = params or EntryRuleParams()

    if not crosses_above(prev_close, prev_vwap, close, vwap):
        return None

    reasons: list[ReasonCode] = [ReasonCode.ENTRY_CROSS]

    if params.min_vol_ratio is not None:
        if vol_ratio is None or float(vol_ratio) < float(params.min_vol_ratio):
            return None
        reasons.append(ReasonCode.VOL_CONFIRM)

    # Limit price rule (v1): place limit at current VWAP
    limit_px = float(vwap)

    return EntrySignal(
        ts=int(ts),
        side=side,
        limit_px=limit_px,
        reasons=reasons,
    )