"""
src/generator.py
Génère une série de transactions simulées : timestamp, prix, volume.
"""

import random
import csv
from datetime import datetime, timedelta
from pathlib import Path

def generate_trades(
    start_price: float = 100.0,
    n_trades: int = 5000,
    volatility: float = 0.002,
    avg_volume: int = 50,
    seed: int = 42,
    outfile: str = "data/sample_trades.csv",
):
    random.seed(seed)
    price = start_price
    t = datetime.now()

    Path(outfile).parent.mkdir(parents=True, exist_ok=True)
    with open(outfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "price", "volume"])
        for _ in range(n_trades):
            # simulate small random drift
            price *= 1 + random.gauss(0, volatility)
            price = round(price, 2)
            volume = max(1, int(random.expovariate(1 / avg_volume)))
            writer.writerow([t.isoformat(), price, volume])
            t += timedelta(seconds=1)

    print(f"{n_trades} transactions sauvegardées dans {outfile}")

if __name__ == "__main__":
    generate_trades()
