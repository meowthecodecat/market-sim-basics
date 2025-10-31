# src/audit_alignment.py
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def load_csv(p):
    p = Path(p); assert p.exists(), f"Introuvable: {p}"
    return pd.read_csv(p)

def sign_series(x: pd.Series) -> pd.Series:
    out = np.where(x > 0, 1, np.where(x < 0, -1, 0))
    return pd.Series(out, index=x.index, dtype=int)

def corr_pair(x: pd.Series, y: pd.Series) -> float:
    z = pd.concat([x, y], axis=1).dropna()
    if z.shape[0] < 3:
        return np.nan
    return z.iloc[:,0].corr(z.iloc[:,1])

def audit(candles_csv, labels_csv, signals_csv, sig_col=None, horizon=3, max_lag=5):
    c = load_csv(candles_csv)      # ex: data/btc_usd_5s.csv
    l = load_csv(labels_csv)       # ex: data/btc_usd_5s_lbl.csv
    s = load_csv(signals_csv)      # ex: data/btc_usd_5s_sig_micro.csv

    for df, name in [(c,"candles"),(l,"labels"),(s,"signals")]:
        assert "t0" in df.columns, f"Colonne t0 manquante dans {name}"
        assert df["t0"].is_monotonic_increasing, f"{name}: t0 non trié"
        assert not df["t0"].duplicated().any(), f"{name}: t0 dupliqué"

    for col in ("open","close"):
        assert col in c.columns, f"Colonne manquante dans candles: {col}"

    if sig_col is None:
        if "signal_micro" in s.columns: sig_col = "signal_micro"
        elif "signal_candle" in s.columns: sig_col = "signal_candle"
        else: raise AssertionError("Aucune colonne signal_* trouvée")

    m = (c[["t0","open","close"]]
         .merge(s[["t0",sig_col]], on="t0", how="left", validate="one_to_one")
         .merge(l[["t0","y"]], on="t0", how="left", validate="one_to_one"))

    m[sig_col] = pd.to_numeric(m[sig_col], errors="coerce").fillna(0).astype(int)

    samebar_ret = (m["close"] - m["open"]) / m["open"]
    samebar_sign = sign_series(samebar_ret)

    fut_ret = (m["close"].shift(-horizon) - m["open"]) / m["open"]
    fut_sign = sign_series(fut_ret)

    print("=== Checks de base ===")
    print(f"rows={len(m)}, signals!=0={int((m[sig_col]!=0).sum())}")
    print("missing labels:", int(m["y"].isna().sum()))
    print("missing fut_ret:", int(fut_ret.isna().sum()))
    print()

    corr_same = corr_pair(m[sig_col], samebar_sign)
    print(f"corr(signal, samebar_sign) = {corr_same:.4f}  (attendu ~0 sans fuite)")

    if "y" in m.columns and m["y"].notna().any():
        y_clean = pd.to_numeric(m["y"], errors="coerce")
        corr_y = corr_pair(m[sig_col], y_clean)
        print(f"corr(signal, y)          = {corr_y:.4f}  (si >>0, fuite probable)")
    print()

    print("=== Balayage lags (signal exécuté après lag bougies) ===")
    best = None
    for lag in range(-max_lag, max_lag+1):
        sig_lag = m[sig_col].shift(lag)
        corr_fut = corr_pair(sig_lag, fut_sign)
        print(f"lag={lag:+d}  corr(signal_lag, fut_sign) = {corr_fut:.4f}")
        if best is None or (pd.notna(corr_fut) and abs(corr_fut) > abs(best[1])):
            best = (lag, corr_fut)
    print(f"=> lag max corr: {best[0]} (corr={best[1]:.4f})\n")

    print("=== 20 premières lignes ===")
    head = m[["t0","open","close",sig_col]].head(20).copy()
    head["samebar_sign"] = samebar_sign.head(20).values
    head["fut_sign(h)"]  = fut_sign.head(20).values
    print(head.to_string(index=False))

    print("\n=== 20 premières lignes avec signal != 0 ===")
    nz = m.loc[m[sig_col]!=0, ["t0","open","close",sig_col]].head(20).copy()
    nz["samebar_sign"] = samebar_sign[m[sig_col]!=0].head(20).values
    nz["fut_sign(h)"]  = fut_sign[m[sig_col]!=0].head(20).values
    print(nz.to_string(index=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candles", required=True)
    ap.add_argument("--labels",  required=True)
    ap.add_argument("--signals", required=True)
    ap.add_argument("--sigcol",  default=None)
    ap.add_argument("--h", type=int, default=3)
    ap.add_argument("--maxlag", type=int, default=5)
    a = ap.parse_args()
    audit(a.candles, a.labels, a.signals, a.sigcol, a.h, a.maxlag)

if __name__ == "__main__":
    main()
