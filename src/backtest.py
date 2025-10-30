# src/backtest.py
"""
Backtest minimal: applique un signal {-1,0,1} sur chandeliers avec coût.
- Entrée à l'open de la bougie suivante
- Sortie après h bougies (t+h) à Close[t+h]
- Coûts = fees_bp en bps + half-spread si micro fourni (optionnel)
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np
from math import sqrt

def _merge(candles: pd.DataFrame, signals: pd.DataFrame, micro: pd.DataFrame | None, sig_col: str) -> pd.DataFrame:
    df = candles.merge(signals[["t0", sig_col]], on="t0", how="left")
    df[sig_col] = df[sig_col].fillna(0).astype(int)
    if micro is not None:
        df = df.merge(micro, on="t0", how="left")
    return df

def run_bt(candles_csv: str, signals_csv: str, out_csv: str,
           horizon: int, fees_bp: float = 0.5,
           micro_csv: str | None = None) -> dict:
    p1 = Path(candles_csv); p2 = Path(signals_csv)
    assert p1.exists() and p2.exists()
    candles = pd.read_csv(p1)
    signals = pd.read_csv(p2)
    micro = pd.read_csv(micro_csv) if micro_csv and Path(micro_csv).exists() else None

    for c in ("t0","open","close"):
        assert c in candles.columns

    # accepte 'signal_candle' ou 'signal_micro'
    if "signal_candle" in signals.columns:
        sig_col = "signal_candle"
    elif "signal_micro" in signals.columns:
        sig_col = "signal_micro"
    else:
        raise AssertionError("Colonne de signal manquante: 'signal_candle' ou 'signal_micro'")

    df = _merge(candles, signals, micro, sig_col)

    # Entrées/sorties
    sig = df[sig_col].astype(int)
    entry_sig = sig.shift(1).fillna(0).astype(int)  # entrer à la prochaine bougie à l'open

    entry_px = df["open"]
    exit_px  = df["close"].shift(-horizon)
    ret_gross = entry_sig * ((exit_px - entry_px) / entry_px)

    # coûts
    fees = abs(entry_sig) * (fees_bp * 1e-4)
    half_spread = 0.0
    if micro is not None and "spread" in df.columns and "mid" in df.columns:
        half_spread = (df["spread"] / df["mid"]).fillna(0.0) / 2.0
    cost = fees + abs(entry_sig) * half_spread
    ret_net = ret_gross - cost

    res = df[["t0"]].copy()
    res["signal"]    = entry_sig
    res["ret_gross"] = ret_gross.fillna(0.0)
    res["ret_net"]   = ret_net.fillna(0.0)
    res.to_csv(out_csv, index=False)

    trades = res[res["signal"] != 0]
    hit = (trades["ret_net"] > 0).mean() if len(trades) else 0.0
    avg = trades["ret_net"].mean() if len(trades) else 0.0
    std = trades["ret_net"].std(ddof=1) if len(trades) > 1 else np.nan
    sharpe = (avg / std * sqrt(252*24*60)) if std and not np.isnan(std) else np.nan

    return {"n_trades": int(trades.shape[0]), "hit_rate": float(hit), "avg_ret": float(avg), "sharpe_like": float(sharpe) if sharpe==sharpe else None}

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candles", required=True)
    ap.add_argument("--signals", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--h", type=int, default=3)
    ap.add_argument("--fees_bp", type=float, default=0.5)
    ap.add_argument("--micro", default=None)
    return ap.parse_args()

def main():
    a = _args()
    stats = run_bt(a.candles, a.signals, a.out, a.h, a.fees_bp, a.micro)
    print(stats)

if __name__ == "__main__":
    main()
