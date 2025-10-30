"""
src/targets.py
Construit des labels directionnels y_{t,h,eps} à partir d'un CSV de chandeliers.
y = +1 si (Close[t+h]-Close[t])/Close[t] > eps
y = -1 si < -eps
y =  0 sinon
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def make_labels(candles_csv: str, out_csv: str, horizon: int, eps: float) -> None:
    assert horizon >= 1
    assert eps >= 0.0
    p = Path(candles_csv); assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)
    for c in ("t0","open","high","low","close"):
        assert c in df.columns, f"Colonne manquante: {c}"
    df["fwd_close"] = df["close"].shift(-horizon)
    ret = (df["fwd_close"] - df["close"]) / df["close"]
    y = np.where(ret > eps, 1, np.where(ret < -eps, -1, 0))
    df["y"] = y
    df.drop(columns=["fwd_close"], inplace=True)
    df.to_csv(out_csv, index=False)

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="candles_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    ap.add_argument("--h", dest="horizon", type=int, default=3)
    ap.add_argument("--eps", dest="eps", type=float, default=0.0005)
    return ap.parse_args()

def main():
    a = _args()
    make_labels(a.candles_csv, a.out_csv, a.horizon, a.eps)

if __name__ == "__main__":
    main()
