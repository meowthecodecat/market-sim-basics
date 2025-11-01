"""
src/patterns_candles.py
Détecteurs de patterns chandeliers. Retour: CSV avec 'signal_candle' ∈ {-1,0,1}.
- Engulfing haussier/baissier
- Hammer / Shooting star
- Inside bar (neutre)
"""

from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def compute_pattern_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les signaux chandeliers en s'appuyant sur les détecteurs internes.
    Retourne un DataFrame aligné sur l'index de df avec:
      - signal_candle: synthèse {-1,0,1}
      - engulfing: {-1,0,1}
      - hammer: 1 si marteau détecté, 0 sinon
      - shooting_star: 1 si shooting star détectée, 0 sinon
      - inside_bar: 1 si inside bar, 0 sinon
    """
    required_cols = {"open", "high", "low", "close"}
    missing = required_cols.difference(df.columns)
    assert not missing, f"Colonnes manquantes pour les patterns: {missing}"

    s_engulf = _engulfing(df)
    s_hammer_like = _hammer_like(df)
    s_inside = _inside_bar(df)

    inside_mask = (
        (df["high"] < df["high"].shift(1)) &
        (df["low"] > df["low"].shift(1))
    )

    indicators = pd.DataFrame(index=df.index)

    primary_signal = (s_engulf + s_hammer_like + s_inside).clip(-1, 1).astype("int8")

    returns = df["close"].pct_change()
    abs_ret = returns.abs()
    rolling_vol = abs_ret.rolling(window=20, min_periods=5).mean()
    dynamic_eps = (
        (rolling_vol * 0.75)
        .fillna(abs_ret.rolling(window=10, min_periods=1).median())
        .clip(lower=1e-4, upper=8e-3)
    )
    returns = returns.fillna(0.0)
    dynamic_eps = dynamic_eps.fillna(2e-4)
    mom_signal = np.where(returns > dynamic_eps, 1, np.where(returns < -dynamic_eps, -1, 0)).astype("int8")

    signal = primary_signal.copy()
    neutral_mask = signal == 0
    signal.loc[neutral_mask] = mom_signal[neutral_mask]

    indicators["signal_candle"] = signal.astype("int8")
    indicators["engulfing"] = s_engulf.astype("int8")
    indicators["hammer"] = (s_hammer_like == 1).astype("int8")
    indicators["shooting_star"] = (s_hammer_like == -1).astype("int8")
    indicators["inside_bar"] = inside_mask.fillna(False).astype("int8")
    indicators["ret_pct"] = returns.astype("float32")
    indicators["mom_threshold"] = dynamic_eps.astype("float32")
    indicators["mom_signal"] = mom_signal.astype("int8")
    return indicators

def _engulfing(df: pd.DataFrame) -> pd.Series:
    o,c,h,l = df["open"], df["close"], df["high"], df["low"]
    body     = c - o
    prev_o   = o.shift(1); prev_c = c.shift(1)
    prevbody = prev_c - prev_o

    bull = (body > 0) & (prevbody < 0) & (o <= prev_c) & (c >= prev_o)
    bear = (body < 0) & (prevbody > 0) & (o >= prev_c) & (c <= prev_o)
    return pd.Series(np.where(bull,1,np.where(bear,-1,0)), index=df.index, dtype="int8")

def _hammer_like(df: pd.DataFrame) -> pd.Series:
    o,c,h,l = df["open"], df["close"], df["high"], df["low"]
    body      = (c - o).abs()
    rng       = (h - l).replace(0, np.nan)

    body_top  = pd.concat([o,c], axis=1).max(axis=1)
    body_bot  = pd.concat([o,c], axis=1).min(axis=1)
    lower_w   = body_bot - l            # distance du bas du corps au plus bas
    upper_w   = h - body_top            # distance du plus haut au haut du corps

    is_hammer = (lower_w > 2*body) & (upper_w < body) & (body/rng < 0.4)
    is_star   = (upper_w > 2*body) & (lower_w < body) & (body/rng < 0.4)

    sig = np.where(is_hammer,1,np.where(is_star,-1,0))
    return pd.Series(sig, index=df.index, dtype="int8")

def _inside_bar(df: pd.DataFrame) -> pd.Series:
    hi, lo = df["high"], df["low"]
    prev_hi, prev_lo = hi.shift(1), lo.shift(1)
    inside = (hi < prev_hi) & (lo > prev_lo)
    # neutre → 0
    return pd.Series(np.where(inside,0,0), index=df.index, dtype="int8")

def detect_signals(candles_csv: str, out_csv: str) -> None:
    p = Path(candles_csv); assert p.exists(), f"Introuvable: {p}"
    df = pd.read_csv(p)
    for c in ("t0","open","high","low","close"):
        assert c in df.columns, f"Colonne manquante: {c}"

    indicators = compute_pattern_indicators(df)
    out = df.copy()
    for col in indicators.columns:
        out[col] = indicators[col].values
    out.to_csv(out_csv, index=False)

def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="candles_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    return ap.parse_args()

def main():
    a = _args()
    detect_signals(a.candles_csv, a.out_csv)

if __name__ == "__main__":
    main()
