"""
src/plotter.py
Affiche un graphique en chandeliers japonais avec volume via mplfinance.
"""

from pathlib import Path
import argparse
import pandas as pd
import mplfinance as mpf

def plot_candles(candles_csv: str, save_prefix: str | None = None) -> None:
    p = Path(candles_csv)
    assert p.exists(), f"Fichier introuvable : {p}"

    df = pd.read_csv(p)
    for col in ("t0","open","high","low","close"):
        assert col in df.columns, f"Colonne manquante : {col}"

    # Datetime en index
    df["t0"] = pd.to_datetime(df["t0"], utc=True, errors="coerce").dt.tz_convert(None)
    df = df.set_index("t0").sort_index()

    # Volume: priorité à quote_volume si présent
    vol_col = "quote_volume" if "quote_volume" in df.columns else ("volume" if "volume" in df.columns else None)
    if vol_col:
        df["Volume"] = pd.to_numeric(df[vol_col], errors="coerce").fillna(0.0)
    else:
        df["Volume"] = 0.0  # pas de volume disponible

    # Renommer pour mplfinance
    df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close"})

    # Style
    style = mpf.make_mpf_style(base_mpf_style="classic", gridstyle="-.", facecolor="white")

    # Arguments mplfinance, sans savefig si None
    kwargs = dict(
        type="candle",
        style=style,
        title="BTC/USD — Chandeliers",
        ylabel="Prix (USD)",
        ylabel_lower="Volume",
        volume=True,
        mav=(5, 20),
        tight_layout=True,
        show_nontrading=False,
    )
    if save_prefix:
        kwargs["savefig"] = f"{save_prefix}_candles.png"

    mpf.plot(df, **kwargs)

def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="candles_csv", required=True)
    ap.add_argument("--save_prefix", type=str, default=None)
    return ap.parse_args()

def main():
    a = _parse_args()
    plot_candles(a.candles_csv, save_prefix=a.save_prefix)

if __name__ == "__main__":
    main()
