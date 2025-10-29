"""
src/plotter.py
Affiche des chandeliers OHLCV depuis un CSV.
"""

from pathlib import Path
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def plot_candles(candles_csv: str) -> None:
    p = Path(candles_csv)
    assert p.exists(), f"Fichier introuvable : {p}"

    df = pd.read_csv(p)
    for col in ("t0","open","high","low","close","volume"):
        assert col in df.columns, f"Colonne manquante : {col}"

    # Axe X en index numérique régulier
    xs = range(len(df))
    o = df["open"].to_list()
    h = df["high"].to_list()
    l = df["low"].to_list()
    c = df["close"].to_list()
    v = df["volume"].fillna(0).astype(int).to_list()

    # Graphique Chandeliers
    plt.figure(figsize=(10,4))
    for i,(op,hi,lo,cl) in enumerate(zip(o,h,l,c)):
        # Mèche
        plt.plot([i,i],[lo,hi])
        # Corps rectangle via 4 segments
        top = max(op,cl); bot = min(op,cl)
        plt.plot([i-0.3, i+0.3],[top,top])
        plt.plot([i-0.3, i+0.3],[bot,bot])
        plt.plot([i-0.3, i-0.3],[bot,top])
        plt.plot([i+0.3, i+0.3],[bot,top])

    plt.title("Chandeliers")
    plt.xlabel("Index bougie")
    plt.ylabel("Prix")
    plt.tight_layout()
    plt.show()

    # Graphique Volumes
    plt.figure(figsize=(10,2.5))
    plt.bar(list(xs), v, width=0.8)
    plt.title("Volume")
    plt.xlabel("Index bougie")
    plt.ylabel("Qty")
    plt.tight_layout()
    plt.show()

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="candles_csv", required=True, help="data/candles_60s.csv")
    return ap.parse_args()

def main() -> None:
    args = _parse_args()
    plot_candles(args.candles_csv)

if __name__ == "__main__":
    main()
