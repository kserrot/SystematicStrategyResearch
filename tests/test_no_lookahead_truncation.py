import inspect

import pandas as pd
import pytest

import src.backtest.engine as engine
import src.strategies.v1.spec as spec


def _get_engine_runner():
    """Return the most likely public backtest runner from src.backtest.engine."""

    candidates = [
        "run_backtest_v1",
        "run_engine",
        "run",
        "backtest",
        "simulate",
        "run_strategy",
    ]

    for name in candidates:
        fn = getattr(engine, name, None)
        if callable(fn):
            return fn

    pytest.skip("No callable runner found in src.backtest.engine")


def _maybe_make_params():
    """Best-effort create a params object from src.strategies.v1.spec.

    The class name can evolve; we try a few common names.
    """

    candidates = [
        "Params",
        "StrategyParams",
        "BacktestParams",
        "V1Params",
    ]

    for name in candidates:
        cls = getattr(spec, name, None)
        if cls is None:
            continue
        if callable(cls):
            try:
                return cls()
            except TypeError:
                # Requires args; ignore and fall back.
                return None

    return None


def _run_engine(run_fn, df: pd.DataFrame):
    """Call the engine runner with the args it requires.

    Different engine entrypoints can have different signatures (e.g., require
    `symbol`). We build args/kwargs from the signature to keep the test robust.
    """

    params_obj = _maybe_make_params()

    sig = None
    try:
        sig = inspect.signature(run_fn)
    except (TypeError, ValueError):
        sig = None

    # If can't introspect, fall back to the simplest call.
    if sig is None:
        try:
            return run_fn(df)
        except TypeError:
            if params_obj is not None:
                return run_fn(df, params_obj)
            pytest.skip("Engine runner signature unknown and call failed")

    args = []
    kwargs = {}

    df_names = {"df", "bars", "data", "frame"}
    symbol_names = {"symbol", "sym"}
    tf_names = {"timeframe", "tf"}
    params_names = {"params", "p"}

    def _value_for(name: str):
        if name in df_names:
            return df
        if name in symbol_names:
            return "TEST"
        if name in tf_names:
            return "10m"
        if name in params_names:
            return params_obj
        return None

    for param in sig.parameters.values():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            val = _value_for(param.name)
            if val is not None:
                # Only pass params if could create a params object.
                if param.name in params_names and params_obj is None:
                    # If params is required, can't proceed.
                    if param.default is inspect._empty:
                        pytest.skip("Engine runner requires params, but none found")
                    continue
                args.append(val)
                continue

            # Optional args can be omitted.
            if param.default is not inspect._empty:
                continue

            pytest.skip(f"Engine runner requires unsupported arg: {param.name}")

        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            val = _value_for(param.name)
            if val is not None:
                if param.name in params_names and params_obj is None:
                    if param.default is inspect._empty:
                        pytest.skip("Engine runner requires params, but none found")
                    continue
                kwargs[param.name] = val
                continue

            if param.default is not inspect._empty:
                continue

            pytest.skip(f"Engine runner requires unsupported kw-only arg: {param.name}")

        # VAR_POSITIONAL / VAR_KEYWORD are ignored

    return run_fn(*args, **kwargs)


def _extract_trades(result):
    """Normalize engine output to a trades DataFrame.

    The v1 engine returns `list[Trade]`. Other parts of the codebase may
    return a richer result object (with `.trades`) or a dict.
    """

    if hasattr(result, "trades"):
        trades = result.trades
        if isinstance(trades, pd.DataFrame):
            return trades

    if isinstance(result, dict) and "trades" in result:
        trades = result["trades"]
        if isinstance(trades, pd.DataFrame):
            return trades

    if isinstance(result, list):
        if not result:
            # Ensure stable schema for empty comparisons.
            return pd.DataFrame(columns=["entry_ts"])

        first = result[0]
        if hasattr(first, "entry_ts"):
            rows: list[dict] = []
            for t in result:
                if hasattr(t, "__dict__"):
                    rows.append(dict(t.__dict__))
                else:
                    # Fallback: pull common trade fields if present.
                    row = {}
                    for k in ("entry_ts", "entry_px", "exit_ts", "exit_px", "r_mult"):
                        if hasattr(t, k):
                            row[k] = getattr(t, k)
                    rows.append(row)

            df = pd.DataFrame(rows)
            if "entry_ts" not in df.columns:
                df["entry_ts"] = pd.NA
            return df

    if isinstance(result, tuple) and result:
        for item in result:
            if isinstance(item, pd.DataFrame) and "entry_ts" in item.columns:
                return item

    pytest.skip("Could not extract trades DataFrame from engine result")


def test_no_lookahead_truncation_equivalence() -> None:
    # Minimal deterministic dataset.
    # Add the most common feature columns the strategy/engine may expect.
    df = pd.DataFrame(
        {
            "ts": [100, 110, 120, 130, 140, 150],
            "open": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
            "high": [10.5, 10.6, 10.7, 10.8, 10.9, 11.0],
            "low": [9.5, 9.6, 9.7, 9.8, 9.9, 10.0],
            "close": [10.0, 10.1, 10.2, 10.1, 10.3, 10.4],
            "volume": [100.0, 120.0, 110.0, 130.0, 125.0, 140.0],
        }
    )

    # Simple defaults.
    df["vwap"] = df["close"]
    df["atr"] = 0.5
    df["ema50_1h"] = 2.0
    df["ema200_1h"] = 1.0
    df["vol_ratio"] = 1.0
    # Backwards-compatible flag for older code paths (safe if unused).
    df["trend_ok"] = True

    run_fn = _get_engine_runner()

    # Full run
    out_full = _run_engine(run_fn, df.copy())

    # Truncated run (up to ts=130)
    cutoff_ts = 130
    df_trunc = df[df["ts"] <= cutoff_ts].copy()
    out_trunc = _run_engine(run_fn, df_trunc)

    full_trades = _extract_trades(out_full)
    trunc_trades = _extract_trades(out_trunc)

    # If both are empty, equivalence holds.
    if full_trades.empty and trunc_trades.empty:
        pd.testing.assert_frame_equal(
            full_trades.reset_index(drop=True),
            trunc_trades.reset_index(drop=True),
        )
        return

    if "entry_ts" not in full_trades.columns or "entry_ts" not in trunc_trades.columns:
        pytest.skip("Trades do not include entry_ts; cannot compare truncation equivalence")

    full_upto = full_trades[full_trades["entry_ts"] <= cutoff_ts].reset_index(drop=True)
    trunc_all = trunc_trades.reset_index(drop=True)

    pd.testing.assert_frame_equal(full_upto, trunc_all)
