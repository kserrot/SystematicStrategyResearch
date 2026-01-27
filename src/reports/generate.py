from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.reports.equity_report import ReportPaths, build_equity_curve, save_report


@dataclass(frozen=True)
class Step7ReportResult:
    out_dir: Path
    paths: ReportPaths
    manifest_json: Path


def _safe_read_summary(summary_json: Path | None) -> dict[str, Any] | None:
    if summary_json is None:
        return None
    if not summary_json.exists():
        return None
    with summary_json.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_report_from_trades(
    trades_csv: Path,
    out_dir: Path,
    *,
    prefix: str = "",
    summary_json: Path | None = None,
) -> Step7ReportResult:
    """
    Step 7 report generator (v1):
      - reads trades.csv (must include net_pnl)
      - writes equity.csv + equity_curve.png + drawdown.png (via equity_report.py)
      - writes a manifest.json with basic stats + pointers to artifacts
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    eq: pd.DataFrame = build_equity_curve(trades_csv)
    paths: ReportPaths = save_report(eq, out_dir=out_dir, prefix=prefix)

    total_net_pnl = float(eq["net_pnl"].sum()) if len(eq) else 0.0
    max_drawdown = float(eq["drawdown"].min()) if len(eq) else 0.0
    n_trades = int(len(eq))

    summary = _safe_read_summary(summary_json)

    manifest = {
        "trades_csv": str(trades_csv),
        "summary_json": str(summary_json) if summary_json is not None else None,
        "n_trades": n_trades,
        "total_net_pnl": total_net_pnl,
        "max_drawdown": max_drawdown,
        "artifacts": {
            "equity_csv": str(paths.equity_csv),
            "equity_png": str(paths.equity_png),
            "drawdown_png": str(paths.drawdown_png),
        },
        "summary": summary,
    }

    pfx = f"{prefix}_" if prefix else ""
    manifest_json = out_dir / f"{pfx}manifest.json"
    with manifest_json.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    return Step7ReportResult(out_dir=out_dir, paths=paths, manifest_json=manifest_json)
