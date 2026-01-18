from __future__ import annotations

import pandas as pd

from src.backtest.fill_model import check_fill, place_limit_order, step_age_and_expire
from src.backtest.types import Trade
from src.strategies.v1.entry import EntryRuleParams, build_entry_signal
from src.strategies.v1.exits import check_long_exit, compute_long_brackets
from src.strategies.v1.spec import ReasonCode, Side, StrategyParams
from src.strategies.v1.trend_filter import trend_ok


def run_backtest_v1(
    frame: pd.DataFrame,
    symbol: str,
    params: StrategyParams,
    entry_params: EntryRuleParams | None = None,
) -> list[Trade]:
    """
    Deterministic backtest engine (no lookahead).

    Expects frame columns (already aligned, no lookahead):
      ts (int), high, low, close (float)
      vwap (float)
      atr (float)  <-- used to set stop/TP brackets at fill
      vol_ratio (float, optional if entry_params.min_vol_ratio is None)
      ema50_1h (float), ema200_1h (float)

    Uses:
      - Trend filter (1h)
      - Entry: 10m cross above VWAP (+ optional vol confirm)
      - Limit order: placed next bar, fill rule low<=limit<=high, expiry N bars
      - Exit: ATR stop + R-multiple take profit (+ optional time stop)
    """
    if entry_params is None:
        entry_params = EntryRuleParams(min_vol_ratio=None)

    required_cols = {"ts", "high", "low", "close", "vwap", "atr", "ema50_1h", "ema200_1h"}
    missing = required_cols - set(frame.columns)
    if missing:
        raise ValueError(f"frame missing columns: {sorted(missing)}")

    trades: list[Trade] = []

    state = "FLAT"
    pending_order = None
    position = None
    # position dict keys when in a trade:
    # {side, entry_ts, entry_px, hold_bars, reasons, brackets}

    frame = frame.reset_index(drop=True)

    for i in range(1, len(frame)):
        row = frame.loc[i]
        prev = frame.loc[i - 1]

        ts = int(row["ts"])
        bar = {"low": float(row["low"]), "high": float(row["high"])}

        # -------------------------
        # IN_POSITION: manage exits
        # -------------------------
        if state == "IN_POSITION":
            assert position is not None
            position["hold_bars"] += 1

            # 1) Check STOP / TAKE PROFIT using bar range
            exit_px, exit_reason = check_long_exit(
                low=float(row["low"]),
                high=float(row["high"]),
                brackets=position["brackets"],
            )
            if exit_px is not None:
                trades.append(
                    Trade(
                        symbol=symbol,
                        side=position["side"],
                        entry_ts=position["entry_ts"],
                        entry_px=position["entry_px"],
                        exit_ts=ts,
                        exit_px=float(exit_px),
                        reasons=position["reasons"] + [exit_reason],
                    )
                )
                state = "FLAT"
                position = None
                continue

            # 2) Optional time stop as fallback
            if params.time_stop_bars is not None:
                if position["hold_bars"] >= int(params.time_stop_bars):
                    trades.append(
                        Trade(
                            symbol=symbol,
                            side=position["side"],
                            entry_ts=position["entry_ts"],
                            entry_px=position["entry_px"],
                            exit_ts=ts,
                            exit_px=float(row["close"]),
                            reasons=position["reasons"] + [ReasonCode.TIME_STOP],
                        )
                    )
                    state = "FLAT"
                    position = None

            continue

        # --------------------------------
        # ORDER_PENDING: check fill/expiry
        # --------------------------------
        if state == "ORDER_PENDING":
            assert pending_order is not None

            pending_order, filled = check_fill(pending_order, bar_ts=ts, bar=bar)
            if filled:
                # Enter position at limit fill price
                state = "IN_POSITION"

                entry_px = float(pending_order.fill_px)
                atr = float(row["atr"])  # ATR from fill bar (no lookahead)

                brackets = compute_long_brackets(
                    entry_px=entry_px,
                    atr=atr,
                    atr_mult=float(params.atr_stop_mult),
                    take_profit_r=float(params.take_profit_r),
                )

                position = {
                    "side": pending_order.side,
                    "entry_ts": int(pending_order.fill_ts),
                    "entry_px": entry_px,
                    "hold_bars": 0,
                    "reasons": pending_order.reasons.copy(),
                    "brackets": brackets,
                }

                pending_order = None
                continue

            pending_order, expired = step_age_and_expire(pending_order)
            if expired:
                state = "FLAT"
                pending_order = None
            continue

        # --------------------------
        # FLAT: trend + entry signal
        # --------------------------
        if state == "FLAT":
            tr = trend_ok(float(row["ema50_1h"]), float(row["ema200_1h"]))
            if not tr.ok:
                continue

            vol_ratio = float(row["vol_ratio"]) if "vol_ratio" in frame.columns else None

            sig = build_entry_signal(
                ts=int(prev["ts"]),
                prev_close=float(prev["close"]),
                prev_vwap=float(prev["vwap"]),
                close=float(row["close"]),
                vwap=float(row["vwap"]),
                side=Side.LONG,
                vol_ratio=vol_ratio,
                params=entry_params,
            )
            if sig is None:
                continue

            # Place limit order on next bar (this current bar)
            pending_order = place_limit_order(
                next_bar_ts=ts,
                side=sig.side,
                limit_px=sig.limit_px,
                expiry_bars=params.limit_expiry_bars,
            )
            pending_order.reasons = sig.reasons + pending_order.reasons
            state = "ORDER_PENDING"

    return trades
