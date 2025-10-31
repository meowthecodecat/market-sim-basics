"""
Utilities to aggregate trade ticks into OHLCV candles.
Includes CSV helpers as well as in-memory aggregation for live usage.
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np
from pandas.api.types import is_numeric_dtype

def aggregate_trades_df(df: pd.DataFrame, dt_sec: int) -> pd.DataFrame:
    """
    Aggregate a DataFrame of trades into OHLCV candles.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain at least columns {timestamp, price, volume}. Timestamps can be
        ISO strings or numeric epochs (s / ms / ns).
    dt_sec : int
        Candle length in seconds.

    Returns
    -------
    pd.DataFrame
        Columns: t0 (ISO UTC string), open, high, low, close, volume, quote_volume.
    """
    assert dt_sec >= 1, "dt_sec doit etre >= 1"
    if df.empty:
        return pd.DataFrame(columns=["t0", "open", "high", "low", "close", "volume", "quote_volume"])

    work = df.copy()
    work.columns = [c.lower() for c in work.columns]

    required = {"timestamp", "price", "volume"}
    missing = required.difference(work.columns)
    assert not missing, f"Colonnes manquantes pour l'aggregation: {missing}"

    ts = work["timestamp"]
    if is_numeric_dtype(ts):
        ts = ts.astype("int64")
        unit = "s"
        if (ts > 1e15).any():
            unit = "ns"
        elif (ts > 1e12).any():
            unit = "ms"
        work["timestamp"] = pd.to_datetime(ts, unit=unit, utc=True, errors="coerce")
    else:
        work["timestamp"] = pd.to_datetime(ts, utc=True, errors="coerce")

    work["price"] = pd.to_numeric(work["price"], errors="coerce")
    work["volume"] = pd.to_numeric(work["volume"], errors="coerce")

    work = work.dropna(subset=["timestamp", "price", "volume"]).sort_values("timestamp", kind="stable")
    if work.empty:
        return pd.DataFrame(columns=["t0", "open", "high", "low", "close", "volume", "quote_volume"])

    rule = f"{dt_sec}s"
    o = work.set_index("timestamp")

    agg = pd.DataFrame({
        "open": o["price"].resample(rule).first(),
        "high": o["price"].resample(rule).max(),
        "low": o["price"].resample(rule).min(),
        "close": o["price"].resample(rule).last(),
        "volume": o["volume"].resample(rule).sum(),
    })
    agg["quote_volume"] = (o["price"] * o["volume"]).resample(rule).sum()
    agg = agg.dropna(subset=["open", "high", "low", "close"])

    agg = agg.reset_index().rename(columns={"timestamp": "t0"})
    agg["t0"] = agg["t0"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return agg

def build_candles(in_csv: str, out_csv: str, dt_sec: int) -> None:
    assert dt_sec >= 1, "dt_sec doit etre >= 1"
    p_in = Path(in_csv)
    p_out = Path(out_csv)
    assert p_in.exists(), f"Fichier introuvable : {p_in}"

    df = pd.read_csv(p_in)

    cols = {c.lower(): c for c in df.columns}
    assert "timestamp" in cols, "Colonne 'timestamp' manquante"
    assert "price" in cols, "Colonne 'price' manquante"
    vol_col = cols.get("volume") or cols.get("qty")
    assert vol_col, "Colonne 'volume' ou 'qty' manquante"

    df = df.rename(columns={
        cols["timestamp"]: "timestamp",
        cols["price"]: "price",
        vol_col: "volume",
    })

    agg = aggregate_trades_df(df, dt_sec)

    p_out.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(p_out, index=False)

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True, help="data/*_trades.csv")
    ap.add_argument("--out", dest="out_csv", required=True, help="data/*_candles_XXs.csv")
    ap.add_argument("--dt", dest="dt_sec", type=int, default=60, help="Taille de bougie en secondes")
    return ap.parse_args()

def main() -> None:
    args = _parse_args()
    build_candles(args.in_csv, args.out_csv, args.dt_sec)

if __name__ == "__main__":
    main()
