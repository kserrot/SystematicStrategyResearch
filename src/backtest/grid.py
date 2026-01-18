from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.backtest.costs import apply_costs
from src.backtest.engine import run_backtest_v1
from src.backtest.metrics import compute_metrics, metrics_to_dict
from src.strategies.v1.entry import EntryRuleParams
from src.strategies.v1.spec import StrategyParams


@dataclass(frozen=True)
class GridResult:
    params: dict[str, Any]
    metrics: dict[str, Any]


def _run_one(
    frame: pd.DataFrame,
    symbol: str,
    strat_params: StrategyParams,
    entry_params: EntryRuleParams,
) -> dict[str, Any]:
    trades = run_backtest_v1(
        frame,
        symbol=symbol,
        params=strat_params,
        entry_params=entry_params,
    )
    pnl_rows = [apply_costs(t, strat_params) for t in trades]
    net_pnls = [r.net_pnl for r in pnl_rows]
    m = compute_metrics(net_pnls)
    return metrics_to_dict(m)


def run_grid_on_train(
    train: pd.DataFrame,
    symbol: str,
    grid: list[dict[str, Any]],
) -> tuple[list[GridResult], dict[str, Any]]:
    """
    Runs param grid on train split and selects best by total_net_pnl.
    Grid item format:
      {
        "strategy": { ... StrategyParams fields ... },
        "entry": { ... EntryRuleParams fields ... },
      }
    Returns (all_results, best_grid_item).
    """
    results: list[GridResult] = []
    best_item: dict[str, Any] | None = None
    best_score = float("-inf")

    for item in grid:
        strat = StrategyParams(**item.get("strategy", {}))
        entry = EntryRuleParams(**item.get("entry", {}))

        m = _run_one(train, symbol=symbol, strat_params=strat, entry_params=entry)
        results.append(GridResult(params=item, metrics=m))

        score = float(m.get("total_net_pnl", 0.0))
        if score > best_score:
            best_score = score
            best_item = item

    if best_item is None:
        raise ValueError("Grid was empty.")

    return results, best_item


def run_walkforward_abc(
    train: pd.DataFrame,
    validate: pd.DataFrame,
    test: pd.DataFrame,
    symbol: str,
    grid: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    1) Run grid on A, pick best by total_net_pnl
    2) Evaluate best on B and C
    """
    all_results, best_item = run_grid_on_train(train, symbol=symbol, grid=grid)

    best_strat = StrategyParams(**best_item.get("strategy", {}))
    best_entry = EntryRuleParams(**best_item.get("entry", {}))

    b_metrics = _run_one(validate, symbol=symbol, strat_params=best_strat, entry_params=best_entry)
    c_metrics = _run_one(test, symbol=symbol, strat_params=best_strat, entry_params=best_entry)

    runs_df = pd.DataFrame(
        [
            {
                "strategy": r.params.get("strategy", {}),
                "entry": r.params.get("entry", {}),
                **r.metrics,
            }
            for r in all_results
        ]
    )

    return {
        "best_params": best_item,
        "validate_metrics": b_metrics,
        "test_metrics": c_metrics,
        "train_grid_runs": runs_df,
    }
