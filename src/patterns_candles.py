"""
src/patterns_candles.py
Détecteurs de patterns chandeliers. Retour: CSV avec 'signal_candle' ∈ {-1,0,1}.
- Engulfing haussier/baissier
- Hammer / Shooting star
- Inside bar (neutre)
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def _engulfing(df: pd.DataFrame) -> pd.Series:
    o,c,h,l = df["open"], df["close"], df["high"], df["low"]
    body     = c - o
    prev_o   = o.shift(1); prev_c = c.shift(1)
    prevbody = prev_c - prev_o

    bull = (body > 0) & (prevbody < 0) & (o <= prev_c) & (c >= prev_o)
    bear = (body < 0) & (prevbody > 0) & (o >= prev_c) & (c <= prev_o)
    return pd.Series(np.where(bull,1,np.where(bear,-1,0)), index=df.index, dtype="int8")

def _hammer_like(df: pd.DataFrame) -> pd.Series:
    o,c,h,l = df["open"], df["close"], df["high"], df["low"]
    body      = (c - o).abs()
    rng       = (h - l).replace(0, np.nan)

    body_top  = pd.concat([o,c], axis=1).max(axis=1)
    body_bot  = pd.concat([o,c], axis=1).min(axis=1)
    lower_w   = body_bot - l            # distance du bas du corps au plus bas
    upper_w   = h - body_top            # distance du plus haut au haut du corps

    is_hammer = (lower_w > 2*body) & (upper_w < body) & (body/rng < 0.4)
    is_star   = (upper_w > 2*body) & (lower_w < body) & (body/rng < 0.4)

    sig = np.where(is_hammer,1,np.where(is_star,-1,0))
    return pd.Series(sig, index=df.index, dtype="int8")

def _inside_bar(df: pd.DataFrame) -> pd.Series:
    hi, lo = df["high"], df["low"]
    prev_hi, prev_lo = hi.shift(1), lo.shift(1)
    inside = (hi < prev_hi) & (lo > prev_lo)
    # neutre → 0
    return pd.Series(np.where(inside,0,0), index=df.index, dtype="int8")

def detect_signals(candles_csv: str, out_csv: str) -> None:
    p = Path(candles_csv); assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)
    for c in ("t0","open","high","low","close"):
        assert c in df.columns, f"Colonne manquante: {c}"

    s1 = _engulfing(df)
    s2 = _hammer_like(df)
    s3 = _inside_bar(df)

    sig = (s1 + s2 + s3).clip(-1,1).astype("int8")
    out = df.copy()
    out["signal_candle"] = sig
    out.to_csv(out_csv, index=False)

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="candles_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    return ap.parse_args()

def main():
    a = _args()
    detect_signals(a.candles_csv, a.out_csv)

if __name__ == "__main__":
    main()
