# src/features.py
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def build_features(candles_csv: str, out_csv: str) -> None:
    p = Path(candles_csv); assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)

    for col in ("open","high","low","close","volume"):
        assert col in df.columns, f"Colonne manquante: {col}"
    assert len(df) > 0, "CSV vide"

    # Retours
    df["ret"] = df["close"].pct_change()
    df["logret"] = np.log(df["close"]).diff()

    # Volatilité rolling
    df["vol_10"] = df["logret"].rolling(10).std() * np.sqrt(10)
    df["vol_30"] = df["logret"].rolling(30).std() * np.sqrt(30)

    # Momentum
    df["mom_5"] = df["close"].pct_change(5)
    df["mom_10"] = df["close"].pct_change(10)

    # RSI(14) simple
    delta = df["close"].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    rs = up / dn
    df["rsi_14"] = 100 - 100 / (1 + rs)

    # Z-score volume
    vol_roll_mean = df["volume"].rolling(30).mean()
    vol_roll_std = df["volume"].rolling(30).std().replace(0, np.nan)
    df["vol_z"] = (df["volume"] - vol_roll_mean) / vol_roll_std

    df.to_csv(out_csv, index=False)

def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="candles_csv", required=True)
    ap.add_argument("--out", dest="out_csv",     required=True)
    return ap.parse_args()

def main():
    a = _parse_args()
    build_features(a.candles_csv, a.out_csv)

if __name__ == "__main__":
    main()
