# src/signals_micro.py
"""
Génère un signal {-1,0,1} à partir du carnet d'ordres agrégé.
Buy si imbalance > τ et spread faible, Sell si imbalance < -τ.
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def build(micro_csv: str, out_csv: str, tau: float = 0.2, max_spread_bp: float = 5.0) -> None:
    p = Path(micro_csv)
    assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)

    for c in ("t0","mid","spread","depth_imb"):
        assert c in df.columns, f"Colonne manquante: {c}"

    spread_bp = (df["spread"] / df["mid"]) * 1e4
    df["signal_micro"] = 0
    buy  = (df["depth_imb"] >  tau) & (spread_bp < max_spread_bp)
    sell = (df["depth_imb"] < -tau) & (spread_bp < max_spread_bp)
    df.loc[buy,  "signal_micro"] =  1
    df.loc[sell, "signal_micro"] = -1

    df[["t0","signal_micro"]].to_csv(out_csv, index=False)

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="micro_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    ap.add_argument("--tau", type=float, default=0.2)
    ap.add_argument("--max_spread_bp", type=float, default=5.0)
    return ap.parse_args()

def main():
    a = _args()
    build(a.micro_csv, a.out_csv, a.tau, a.max_spread_bp)

if __name__ == "__main__":
    main()
