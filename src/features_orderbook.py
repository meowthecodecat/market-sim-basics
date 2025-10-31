# src/features_orderbook.py
"""
Construit des features microstructure à partir de data/kraken_topbook.csv.
Nettoie les spreads négatifs (carnets crossed) avant agrégation.
Sortie : t0, mid, spread, ofi, depth_imb
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def _ofi(bid_px, bid_qty, ask_px, ask_qty):
    dbp, dap = bid_px.diff(), ask_px.diff()
    dbq, daq = bid_qty.diff(), ask_qty.diff()
    c_bid = ((dbp > 0).astype(int) * bid_qty.shift(1)) + ((dbp == 0).astype(int) * dbq.clip(lower=0)) \
          - ((dbp < 0).astype(int) * bid_qty.shift(1)) - ((dbp == 0).astype(int) * (-dbq.clip(upper=0)))
    c_ask = -((dap < 0).astype(int) * ask_qty.shift(1)) - ((dap == 0).astype(int) * daq.clip(lower=0)) \
            + ((dap > 0).astype(int) * ask_qty.shift(1)) + ((dap == 0).astype(int) * (-daq.clip(upper=0)))
    return (c_bid + c_ask).fillna(0.0)

def build_from_topbook(topbook_csv: str, out_csv: str, resample_sec: int = 1):
    p = Path(topbook_csv); assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)

    need = ["timestamp","bid_px","bid_qty","ask_px","ask_qty","mid","spread","bid_depth_qty","ask_depth_qty"]
    for c in need:
        assert c in df.columns, f"Colonne manquante: {c}"

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").set_index("timestamp")

    # Numérisation
    for c in ["bid_px","bid_qty","ask_px","ask_qty","mid","spread","bid_depth_qty","ask_depth_qty"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Recalcule mid/spread et nettoie les carnets crossed
    df["mid"]    = (df["bid_px"] + df["ask_px"]) / 2.0
    df["spread"] = (df["ask_px"] - df["bid_px"]).clip(lower=0.0)
    df = df[df["spread"].notna()]

    # Features classiques
    df["ofi"] = _ofi(df["bid_px"], df["bid_qty"], df["ask_px"], df["ask_qty"])
    denom = (df["bid_depth_qty"] + df["ask_depth_qty"]).replace(0, np.nan)
    df["depth_imb"] = ((df["bid_depth_qty"] - df["ask_depth_qty"]) / denom).fillna(0.0)

    # Agrégation temporelle
    rule = f"{int(resample_sec)}s"
    agg = df[["mid","spread","ofi","depth_imb"]].resample(rule, label="right", closed="right").last()
    agg["spread"] = agg["spread"].clip(lower=0.0)
    agg = agg.ffill()

    # Enrichissement de features dérivées
    agg["spread_bp"] = ((agg["spread"] / agg["mid"]) * 1e4).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    agg["mid_ret_1"] = agg["mid"].pct_change().fillna(0.0)
    agg["mid_ret_3"] = agg["mid"].pct_change(3).fillna(0.0)

    span_fast = max(int(3), 1)
    span_slow = max(int(12), span_fast + 1)
    agg["depth_ema_fast"] = agg["depth_imb"].ewm(span=span_fast, adjust=False).mean().fillna(0.0)
    agg["depth_ema_slow"] = agg["depth_imb"].ewm(span=span_slow, adjust=False).mean().fillna(0.0)
    agg["depth_trend"] = (agg["depth_ema_fast"] - agg["depth_ema_slow"]).fillna(0.0)
    agg["depth_vol"] = agg["depth_imb"].rolling(window=span_slow, min_periods=1).std().fillna(0.0)

    agg["ofi_ema"] = agg["ofi"].ewm(span=max(span_fast, 2), adjust=False).mean().fillna(0.0)
    agg["ofi_z"] = (agg["ofi_ema"] / (agg["ofi"].rolling(window=span_slow, min_periods=1).std().replace(0, np.nan))).fillna(0.0)

    # Sortie finale
    out = agg.reset_index().rename(columns={"timestamp":"t0"})
    out["t0"] = out["t0"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="topbook_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    ap.add_argument("--dt", dest="resample_sec", type=int, default=1)
    return ap.parse_args()

def main():
    a = _args()
    build_from_topbook(a.topbook_csv, a.out_csv, a.resample_sec)

if __name__ == "__main__":
    main()
