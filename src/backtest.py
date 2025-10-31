# src/backtest.py
"""
Backtest causal minimal pour signaux {-1,0,1}.
Les coûts sont bornés à 0 pour éviter un rebate lié à des spreads négatifs.
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np
from math import sqrt

def _load_csv(path: str) -> pd.DataFrame:
    p = Path(path); assert p.exists(), f"Introuvable: {p}"
    return pd.read_csv(p)

def _pick_signal_col(df_sig: pd.DataFrame) -> str:
    if "signal_candle" in df_sig.columns: return "signal_candle"
    if "signal_micro"  in df_sig.columns: return "signal_micro"
    raise AssertionError("Colonne de signal manquante.")

def _merge_align(df_c, df_s, df_m, sig_col, signal_lag):
    out = df_c.merge(df_s[["t0", sig_col]], on="t0", how="left")
    out[sig_col] = pd.to_numeric(out[sig_col], errors="coerce").fillna(0).astype(int)
    out[sig_col] = out[sig_col].shift(signal_lag).fillna(0).astype(int)
    if df_m is not None:
        out = out.merge(df_m[["t0","mid","spread"]], on="t0", how="left")
    return out

def run_bt(candles_csv, signals_csv, out_csv, horizon, fees_bp=0.5, micro_csv=None, signal_lag=1):
    df_c = _load_csv(candles_csv)
    df_s = _load_csv(signals_csv)
    df_m = _load_csv(micro_csv) if micro_csv and Path(micro_csv).exists() else None
    for c in ("t0","open","close"): assert c in df_c.columns

    sig_col = _pick_signal_col(df_s)
    df = _merge_align(df_c, df_s, df_m, sig_col, signal_lag)

    sig = pd.to_numeric(df[sig_col], errors="coerce").fillna(0).astype(int)
    entry_sig = sig
    entry_px  = pd.to_numeric(df["open"], errors="coerce")
    exit_px   = pd.to_numeric(df["close"].shift(-horizon), errors="coerce")

    fut_ret = (exit_px - entry_px) / entry_px
    ret_gross = entry_sig * fut_ret

    # Coûts bornés
    fees = (fees_bp * 1e-4) * entry_sig.abs()
    if df_m is not None and "spread" in df.columns and "mid" in df.columns:
        half_spread = (pd.to_numeric(df["spread"], errors="coerce") /
                       pd.to_numeric(df["mid"], errors="coerce") / 2.0).clip(lower=0.0).fillna(0.0)
    else:
        half_spread = 0.0

    cost = fees + entry_sig.abs() * half_spread
    ret_net = ret_gross - cost

    res = pd.DataFrame({
        "t0": df["t0"],
        "signal": entry_sig,
        "ret_gross": ret_gross.fillna(0.0),
        "ret_net": ret_net.fillna(0.0),
        "fut_ret": fut_ret.fillna(0.0),
    })
    res["fut_sign"] = np.sign(res["fut_ret"]).astype(int)
    res = res.loc[exit_px.notna()]
    res.to_csv(out_csv, index=False)

    trades = res[res["signal"] != 0]
    n = len(trades)
    hit = (trades["ret_net"] > 0).mean() if n else 0.0
    avg = trades["ret_net"].mean() if n else 0.0
    std = trades["ret_net"].std(ddof=1) if n > 1 else np.nan
    sharpe = (avg/std*np.sqrt(252*24*60)) if std and not np.isnan(std) else np.nan

    if n:
        labels = trades["fut_sign"]
        valid = labels != 0
        dir_hit = ((np.sign(trades.loc[valid, "signal"]) == labels[valid]).mean()
                   if valid.any() else None)
        tp = int(((trades["signal"] == 1) & (trades["fut_ret"] > 0)).sum())
        tn = int(((trades["signal"] == -1) & (trades["fut_ret"] < 0)).sum())
        fp = int(((trades["signal"] == 1) & (trades["fut_ret"] <= 0)).sum())
        fn = int(((trades["signal"] == -1) & (trades["fut_ret"] >= 0)).sum())
    else:
        dir_hit = None
        tp = tn = fp = fn = 0

    return {
        "n_trades": n,
        "hit_rate": float(hit),
        "avg_ret": float(avg),
        "sharpe_like": float(sharpe) if sharpe==sharpe else None,
        "dir_hit_rate": float(dir_hit) if dir_hit is not None else None,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candles", required=True)
    ap.add_argument("--signals", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--h", type=int, default=3)
    ap.add_argument("--fees_bp", type=float, default=0.5)
    ap.add_argument("--micro", default=None)
    ap.add_argument("--signal_lag", type=int, default=1)
    return ap.parse_args()

def main():
    a = _args()
    stats = run_bt(a.candles, a.signals, a.out, a.h, a.fees_bp, a.micro, a.signal_lag)
    print(stats)

if __name__ == "__main__":
    main()
