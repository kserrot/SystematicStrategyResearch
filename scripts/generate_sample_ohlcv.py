# Create sample data
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random

OUT = Path("data/raw/btcusdt_1h_sample.csv")

def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    start = datetime.now(timezone.utc) - timedelta(days=14)
    rows = []
    price = 43000.0

    for i in range(14 * 24):
        ts = start + timedelta(hours=i)
        drift = random.uniform(-0.012, 0.012)
        open_ = price
        close = max(1.0, open_ * (1 + drift))
        high = max(open_, close) * (1 + random.uniform(0.0, 0.004))
        low = min(open_, close) * (1 - random.uniform(0.0, 0.004))
        vol = random.uniform(10, 250)
        price = close
        rows.append([ts.isoformat(), open_, high, low, close, vol])

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "open", "high", "low", "close", "volume"])
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows -> {OUT}")

if __name__ == "__main__":
    main()