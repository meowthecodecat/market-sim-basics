"""
src/features_orderbook.py
Construit des features microstructure à partir de data/kraken_topbook.csv
Colonnes attendues: timestamp,symbol,bid_px,bid_qty,ask_px,ask_qty,mid,spread,bid_depth_qty,ask_depth_qty
Sortie: CSV aligné temporellement avec:
- mid, spread
- depth_imb = (bid_depth - ask_depth) / (bid_depth + ask_depth)
- OFI (Order Flow Imbalance) au BBO selon variation prix/qty au niveau 1
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def _ofi(bid_px, bid_qty, ask_px, ask_qty) -> pd.Series:
    # Cont et al. OFI approximation au BBO
    bp, bq = bid_px, bid_qty
    ap, aq = ask_px, ask_qty
    dbp = bp.diff()
    dap = ap.diff()
    dbq = bq.diff()
    daq = aq.diff()

    # contributions
    c_bid = ( (dbp > 0).astype(int) * bq.shift(1) ) + ( (dbp == 0).astype(int) * dbq.clip(lower=0) ) \
          - ( (dbp < 0).astype(int) * bq.shift(1) ) - ( (dbp == 0).astype(int) * (-dbq.clip(upper=0)) )
    c_ask = - ( (dap < 0).astype(int) * aq.shift(1) ) - ( (dap == 0).astype(int) * daq.clip(lower=0) ) \
            + ( (dap > 0).astype(int) * aq.shift(1) ) + ( (dap == 0).astype(int) * (-daq.clip(upper=0)) )
    ofi = c_bid + c_ask
    return ofi.fillna(0.0)

def build_from_topbook(topbook_csv: str, out_csv: str, resample_sec: int = 1) -> None:
    p = Path(topbook_csv); assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)

    need = ["timestamp","bid_px","bid_qty","ask_px","ask_qty","mid","spread","bid_depth_qty","ask_depth_qty"]
    for c in need:
        assert c in df.columns, f"Colonne manquante: {c}"

    # timestamps UTC
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.assign(timestamp=ts).dropna(subset=["timestamp"]).sort_values("timestamp", kind="stable")
    df = df.set_index("timestamp")

    # OFI + déséquilibre profondeur
    df["ofi"] = _ofi(df["bid_px"], df["bid_qty"], df["ask_px"], df["ask_qty"])
    denom = (df["bid_depth_qty"] + df["ask_depth_qty"]).replace(0, np.nan)
    df["depth_imb"] = (df["bid_depth_qty"] - df["ask_depth_qty"]) / denom
    df["depth_imb"] = df["depth_imb"].fillna(0.0)

    # Resample propre pour aligner avec bougies courtes (ex. 1s ou 5s)
    rule = f"{int(resample_sec)}s"
    agg = df[["mid","spread","ofi","depth_imb"]].resample(rule).last().ffill()

    agg = agg.reset_index().rename(columns={"timestamp":"t0"})
    agg["t0"] = agg["t0"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    agg.to_csv(out_csv, index=False)

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
