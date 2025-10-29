"""
src/candles.py
Agrège des transactions (timestamp,price,volume) en chandeliers OHLCV.
Entrée : CSV de trades triés par timestamp.
Sortie : CSV de chandeliers.
"""

from pathlib import Path
import argparse
import pandas as pd

def build_candles(in_csv: str, out_csv: str, dt_sec: int) -> None:
    assert dt_sec >= 1, "dt_sec doit être >= 1"
    p_in = Path(in_csv)
    p_out = Path(out_csv)
    assert p_in.exists(), f"Fichier introuvable : {p_in}"

    df = pd.read_csv(p_in)
    # Validations minimales
    for col in ("timestamp", "price", "volume"):
        assert col in df.columns, f"Colonne manquante : {col}"

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp", kind="stable")

    # Regroupement par fenêtre temporelle
    # On arrondit à la fenêtre inférieure : 5s → '5s', 60s → '60s'
    rule = f"{dt_sec}s"
    o = df.set_index("timestamp")

    # Open = first, High = max, Low = min, Close = last, Volume = sum
    agg = pd.DataFrame({
        "open":  o["price"].resample(rule).first(),
        "high":  o["price"].resample(rule).max(),
        "low":   o["price"].resample(rule).min(),
        "close": o["price"].resample(rule).last(),
        "volume":o["volume"].resample(rule).sum().astype("Int64"),
    }).dropna(subset=["open","high","low","close"])

    agg = agg.reset_index().rename(columns={"timestamp":"t0"})
    agg["t0"] = agg["t0"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    p_out.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(p_out, index=False)

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True, help="data/sample_trades.csv")
    ap.add_argument("--out", dest="out_csv", required=True, help="data/candles_60s.csv")
    ap.add_argument("--dt", dest="dt_sec", type=int, default=60, help="Taille de bougie en secondes")
    return ap.parse_args()

def main() -> None:
    args = _parse_args()
    build_candles(args.in_csv, args.out_csv, args.dt_sec)

if __name__ == "__main__":
    main()
