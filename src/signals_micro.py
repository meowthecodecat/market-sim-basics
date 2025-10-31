# src/signals_micro.py
"""
Génère des signaux {-1, 0, 1} à partir des features microstructure.
Options :
  --invert 1        -> inverse le sens du signal (utile pour tester mean reversion)
  --use_ofi 1       -> combine la profondeur et le flux d’ordres OFI si dispo
  --w_imb, --w_ofi  -> pondérations respectives de depth_imb et OFI
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def build(
    micro_csv: str,
    out_csv: str,
    tau: float = 0.2,
    max_spread_bp: float = 5.0,
    invert: int = 0,
    use_ofi: int = 0,
    w_imb: float = 1.0,
    w_ofi: float = 1.0,
):
    p = Path(micro_csv)
    assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)

    # Vérifications de colonnes
    for c in ("t0", "mid", "spread", "depth_imb"):
        assert c in df.columns, f"Colonne manquante: {c}"

    if "spread_bp" in df.columns:
        spread_bp = pd.to_numeric(df["spread_bp"], errors="coerce").fillna(0.0)
    else:
        spread_bp = (df["spread"] / df["mid"]) * 1e4

    enriched_cols = {"depth_trend","depth_vol","ofi_z","mid_ret_3","depth_ema_fast"}
    has_enriched = enriched_cols.issubset(df.columns)

    if has_enriched:
        depth_vol = pd.to_numeric(df["depth_vol"], errors="coerce").replace(0.0, np.nan)
        depth_trend = pd.to_numeric(df["depth_trend"], errors="coerce").fillna(0.0)
        depth_fast = pd.to_numeric(df["depth_ema_fast"], errors="coerce").fillna(0.0)
        ofi_z = pd.to_numeric(df["ofi_z"], errors="coerce").clip(-5, 5).fillna(0.0)
        mid_ret = pd.to_numeric(df["mid_ret_3"], errors="coerce").fillna(0.0)
        depth_scale = depth_vol.fillna(depth_vol.median())
        depth_scale = depth_scale.clip(lower=1e-6)
        depth_signal = (depth_trend / depth_scale).clip(-5, 5)
        score = (
            1.6 * depth_signal.fillna(0.0) +
            1.0 * ofi_z +
            0.6 * (mid_ret * 100).clip(-5, 5) +
            0.4 * depth_fast.clip(-1, 1)
        )
    else:
        # Construction d’un score directionnel classique
        if use_ofi and "ofi" in df.columns:
            df["ofi"] = pd.to_numeric(df["ofi"], errors="coerce").fillna(0)
            score = w_imb * df["depth_imb"].fillna(0) + w_ofi * np.tanh(df["ofi"])
        else:
            score = df["depth_imb"].fillna(0)

    # Seuils symétriques
    cond_buy  = (score >  tau) & (spread_bp < max_spread_bp)
    cond_sell = (score < -tau) & (spread_bp < max_spread_bp)

    out = df[["t0"]].copy()
    signal = pd.Series(0, index=out.index, dtype=int)
    signal.loc[cond_buy]  =  1
    signal.loc[cond_sell] = -1

    # Inversion éventuelle (pour tester mean reversion)
    if invert:
        signal = -signal

    out["signal_micro"] = signal.astype(int)
    if has_enriched:
        out["score_micro"] = score.round(6)
    out.to_csv(out_csv, index=False)

    n_sig = (signal != 0).sum()
    msg = f"[signals_micro] {n_sig} signaux generes"
    if has_enriched:
        msg += " (mode enrichi)"
    print(f"{msg} -> {out_csv}")

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="micro_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    ap.add_argument("--tau", type=float, default=0.2, help="Seuil de profondeur")
    ap.add_argument("--max_spread_bp", type=float, default=5.0, help="Spread max en bp")
    ap.add_argument("--invert", type=int, default=0, help="1 pour inverser le signal")
    ap.add_argument("--use_ofi", type=int, default=0, help="1 pour utiliser OFI")
    ap.add_argument("--w_imb", type=float, default=1.0, help="Poids du depth imbalance")
    ap.add_argument("--w_ofi", type=float, default=1.0, help="Poids du flux d’ordres (OFI)")
    return ap.parse_args()

def main():
    a = _args()
    build(
        a.micro_csv,
        a.out_csv,
        a.tau,
        a.max_spread_bp,
        a.invert,
        a.use_ofi,
        a.w_imb,
        a.w_ofi,
    )

if __name__ == "__main__":
    main()
