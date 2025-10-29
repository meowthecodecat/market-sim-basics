# src/plotter.py
from pathlib import Path
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def plot_candles(candles_csv: str, save_prefix: str | None = None, show: bool = True) -> None:
    p = Path(candles_csv)
    assert p.exists(), f"Fichier introuvable : {p}"
    df = pd.read_csv(p)
    for col in ("t0","open","high","low","close","volume"):
        assert col in df.columns, f"Colonne manquante : {col}"

    xs = list(range(len(df)))
    o = df["open"].to_list(); h = df["high"].to_list()
    l = df["low"].to_list();  c = df["close"].to_list()
    v = df["volume"].fillna(0).astype(int).to_list()

    # Prix
    plt.figure(figsize=(10,4))
    for i,(op,hi,lo,cl) in enumerate(zip(o,h,l,c)):
        plt.plot([i,i],[lo,hi])
        top = max(op,cl); bot = min(op,cl)
        plt.plot([i-0.3, i+0.3],[top,top])
        plt.plot([i-0.3, i+0.3],[bot,bot])
        plt.plot([i-0.3, i-0.3],[bot,top])
        plt.plot([i+0.3, i+0.3],[bot,top])
    plt.title("Chandeliers")
    plt.xlabel("Index bougie"); plt.ylabel("Prix"); plt.tight_layout()
    if save_prefix:
        Path(save_prefix).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(f"{save_prefix}_price.png", dpi=150)
    if show:
        plt.show()
    plt.close()

    # Volume
    plt.figure(figsize=(10,2.5))
    plt.bar(xs, v, width=0.8)
    plt.title("Volume")
    plt.xlabel("Index bougie"); plt.ylabel("Qty"); plt.tight_layout()
    if save_prefix:
        plt.savefig(f"{save_prefix}_volume.png", dpi=150)
    if show:
        plt.show()
    plt.close()

def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="candles_csv", required=True, help="data/candles_60s.csv")
    ap.add_argument("--save_prefix", type=str, default=None)
    ap.add_argument("--no_show", action="store_true")
    return ap.parse_args()

def main():
    args = _parse_args()
    plot_candles(args.candles_csv, save_prefix=args.save_prefix, show=not args.no_show)

if __name__ == "__main__":
    main()
