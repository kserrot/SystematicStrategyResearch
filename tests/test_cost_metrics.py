from src.backtest.costs import apply_costs
from src.backtest.metrics import compute_metrics
from src.backtest.types import Trade
from src.strategies.v1.spec import Side, StrategyParams


def test_costs_long_basic_direction():
    t = Trade(
        symbol="X",
        side=Side.LONG,
        entry_ts=0,
        entry_px=100.0,
        exit_ts=1,
        exit_px=110.0,
        reasons=[],
    )
    p = StrategyParams(maker_fee_bps=0.0, slippage_bps=0.0, time_stop_bars=None)
    out = apply_costs(t, p)
    assert out.gross_pnl == 10.0
    assert out.net_pnl == 10.0


def test_metrics_basic():
    m = compute_metrics([1.0, -0.5, 2.0, -1.0])
    assert m.trades == 4
    assert 0.0 <= m.win_rate <= 1.0
