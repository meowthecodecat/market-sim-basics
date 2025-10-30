"""
src/candles.py
Agrège des transactions (timestamp, price, volume|qty) en chandeliers OHLCV.
Ajoute aussi `quote_volume` = somme(price * volume) pour tracer en devise.
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def build_candles(in_csv: str, out_csv: str, dt_sec: int) -> None:
    assert dt_sec >= 1, "dt_sec doit être >= 1"
    p_in = Path(in_csv); p_out = Path(out_csv)
    assert p_in.exists(), f"Fichier introuvable : {p_in}"

    df = pd.read_csv(p_in)

    # Normalisation des colonnes
    cols = {c.lower(): c for c in df.columns}
    assert "timestamp" in cols, "Colonne 'timestamp' manquante"
    assert "price"     in cols, "Colonne 'price' manquante"
    vol_col = cols.get("volume") or cols.get("qty")
    assert vol_col, "Colonne 'volume' ou 'qty' manquante"

    df = df.rename(columns={
        cols["timestamp"]: "timestamp",
        cols["price"]: "price",
        vol_col: "volume"
    })

    # Parse timestamp robuste (ISO ou epoch s/ms/ns)
    if np.issubdtype(df["timestamp"].dtype, np.number):
        ts = df["timestamp"].astype("int64")
        unit = "s"
        if (ts > 1e15).any():
            unit = "ns"
        elif (ts > 1e12).any():
            unit = "ms"
        df["timestamp"] = pd.to_datetime(ts, unit=unit, utc=True, errors="coerce")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    # Types numériques
    df["price"]  = pd.to_numeric(df["price"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    # Nettoyage + tri
    df = df.dropna(subset=["timestamp", "price", "volume"]).sort_values("timestamp", kind="stable")

    # Agrégation temporelle
    rule = f"{dt_sec}s"
    o = df.set_index("timestamp")

    open_  = o["price"].resample(rule).first()
    high_  = o["price"].resample(rule).max()
    low_   = o["price"].resample(rule).min()
    close_ = o["price"].resample(rule).last()
    vol_   = o["volume"].resample(rule).sum()
    qvol_  = (o["price"] * o["volume"]).resample(rule).sum()  # en devise

    agg = pd.DataFrame({
        "open": open_, "high": high_, "low": low_, "close": close_,
        "volume": vol_, "quote_volume": qvol_
    }).dropna(subset=["open","high","low","close"])

    agg = agg.reset_index().rename(columns={"timestamp": "t0"})
    # ISO UTC simple
    agg["t0"] = agg["t0"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    p_out.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(p_out, index=False)

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="in_csv",  required=True, help="data/*_trades.csv")
    ap.add_argument("--out", dest="out_csv", required=True, help="data/*_candles_XXs.csv")
    ap.add_argument("--dt",  dest="dt_sec",  type=int, default=60, help="Taille de bougie en secondes")
    return ap.parse_args()

def main() -> None:
    args = _parse_args()
    build_candles(args.in_csv, args.out_csv, args.dt_sec)

if __name__ == "__main__":
    main()
