from __future__ import annotations

from dataclasses import dataclass

from src.backtest.types import Trade
from src.strategies.v1.spec import Side, StrategyParams


@dataclass(frozen=True)
class TradePnL:
    symbol: str
    side: Side
    entry_ts: int
    exit_ts: int

    entry_px_raw: float
    exit_px_raw: float

    entry_px_eff: float
    exit_px_eff: float

    gross_pnl: float
    slippage_cost: float
    fee_cost: float
    net_pnl: float


def _bps_to_rate(bps: float) -> float:
    return float(bps) / 10000.0


def apply_costs(trade: Trade, params: StrategyParams) -> TradePnL:
    """
    Costs model (simple + realistic enough for v1):
      - slippage_bps applied adverse on entry and exit
      - maker_fee_bps charged on notional on entry and exit

    Assumes qty = 1 unit.
    """
    slip = _bps_to_rate(params.slippage_bps)
    maker_fee = _bps_to_rate(params.maker_fee_bps)

    entry_raw = float(trade.entry_px)
    exit_raw = float(trade.exit_px)

    if trade.side == Side.LONG:
        entry_eff = entry_raw * (1.0 + slip)  # worse entry
        exit_eff = exit_raw * (1.0 - slip)    # worse exit
        gross = exit_raw - entry_raw
        net_move = exit_eff - entry_eff
    else:
        # If you add shorts later:
        entry_eff = entry_raw * (1.0 - slip)
        exit_eff = exit_raw * (1.0 + slip)
        gross = entry_raw - exit_raw
        net_move = entry_eff - exit_eff

    # fees on notional both sides
    fee_entry = abs(entry_eff) * maker_fee
    fee_exit = abs(exit_eff) * maker_fee
    fee_cost = fee_entry + fee_exit

    # slippage cost is the difference between gross move and move after slippage (before fees)
    slippage_cost = gross - net_move

    net = net_move - fee_cost

    return TradePnL(
        symbol=trade.symbol,
        side=trade.side,
        entry_ts=trade.entry_ts,
        exit_ts=trade.exit_ts,
        entry_px_raw=entry_raw,
        exit_px_raw=exit_raw,
        entry_px_eff=entry_eff,
        exit_px_eff=exit_eff,
        gross_pnl=gross,
        slippage_cost=slippage_cost,
        fee_cost=fee_cost,
        net_pnl=net,
    )