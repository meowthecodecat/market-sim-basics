# src/run_all.py
"""
Pipeline complet:
1) (optionnel) Stream Kraken pendant N secondes → data/kraken_trades.csv + data/kraken_topbook.csv
2) Candles (5s, 60s)
3) Labels directionnels
4) Patterns chandeliers
5) Features micro (top-of-book)
6) Signal micro (imbalance)
7) Backtests (patterns vs micro)

Exécution:
  python src/run_all.py --pair BTC/USD --stream_secs 0
  python src/run_all.py --pair BTC/USD --stream_secs 1800  # 30 min
"""

from pathlib import Path
import argparse
import asyncio
import sys

# === imports internes ===
from candles import build_candles
from targets import make_labels
from patterns_candles import detect_signals
from features_orderbook import build_from_topbook
from signals_micro import build as build_micro_signal
from backtest import run_bt

# Kraken WS client
try:
    from crypto.kraken_ws import stream as kraken_stream
    HAS_WS = True
except Exception:
    HAS_WS = False


def ensure_dirs():
    Path("data").mkdir(parents=True, exist_ok=True)

def step_stream(pair: str, depth: int, secs: int,
                trades_csv: str, topbook_csv: str) -> None:
    if secs <= 0:
        print("[stream] skip (secs<=0)")
        return
    if not HAS_WS:
        print("[stream] module crypto.kraken_ws introuvable. Étape ignorée.")
        return
    print(f"[stream] {pair} depth={depth} secs={secs}")
    try:
        asyncio.run(asyncio.wait_for(
            kraken_stream(pair=pair, depth=depth,
                          trades_csv=trades_csv, topbook_csv=topbook_csv),
            timeout=secs
        ))
    except asyncio.TimeoutError:
        print("[stream] terminé (timeout).")
    except Exception as e:
        print(f"[stream] erreur: {e}")

def step_candles(in_csv: str, out_csv: str, dt: int):
    print(f"[candles] {in_csv} -> {out_csv} dt={dt}s")
    build_candles(in_csv, out_csv, dt)

def step_labels(in_csv: str, out_csv: str, h: int, eps: float):
    print(f"[labels] {in_csv} -> {out_csv} h={h} eps={eps}")
    make_labels(in_csv, out_csv, h, eps)

def step_patterns(in_csv: str, out_csv: str):
    print(f"[patterns] {in_csv} -> {out_csv}")
    detect_signals(in_csv, out_csv)

def step_micro_features(in_csv: str, out_csv: str, dt: int):
    print(f"[micro] {in_csv} -> {out_csv} dt={dt}s")
    build_from_topbook(in_csv, out_csv, dt)

def step_micro_signal(in_csv: str, out_csv: str, tau: float, max_spread_bp: float):
    print(f"[signal_micro] {in_csv} -> {out_csv} tau={tau} max_spread_bp={max_spread_bp}")
    build_micro_signal(in_csv, out_csv, tau, max_spread_bp)

def step_backtest(candles_csv: str, signals_csv: str, micro_csv: str,
                  out_csv: str, h: int, fees_bp: float, tag: str):
    print(f"[backtest {tag}] h={h} fees={fees_bp}bp")
    stats = run_bt(candles_csv, signals_csv, out_csv, h, fees_bp, micro_csv)
    print(f"[backtest {tag}] -> {stats}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", type=str, default="BTC/USD")
    ap.add_argument("--depth", type=int, default=25)
    ap.add_argument("--stream_secs", type=int, default=0)

    ap.add_argument("--dt_fast", type=int, default=5)
    ap.add_argument("--dt_slow", type=int, default=60)

    ap.add_argument("--h", type=int, default=3)
    ap.add_argument("--eps", type=float, default=0.0005)

    ap.add_argument("--tau", type=float, default=0.2)
    ap.add_argument("--max_spread_bp", type=float, default=5.0)

    ap.add_argument("--fees_bp", type=float, default=0.5)
    return ap.parse_args()

def main():
    args = parse_args()
    ensure_dirs()

    trades_csv   = "data/kraken_trades.csv"
    topbook_csv  = "data/kraken_topbook.csv"

    # 1) streaming optionnel
    step_stream(args.pair, args.depth, args.stream_secs, trades_csv, topbook_csv)

    # 2) candles
    c_fast = f"data/{args.pair.replace('/','_').lower()}_{args.dt_fast}s.csv"
    c_slow = f"data/{args.pair.replace('/','_').lower()}_{args.dt_slow}s.csv"
    step_candles(trades_csv, c_fast, args.dt_fast)
    step_candles(trades_csv, c_slow, args.dt_slow)

    # 3) labels
    c_fast_lbl = c_fast.replace(".csv", "_lbl.csv")
    c_slow_lbl = c_slow.replace(".csv", "_lbl.csv")
    step_labels(c_fast, c_fast_lbl, args.h, args.eps)
    step_labels(c_slow, c_slow_lbl, args.h, args.eps)

    # 4) patterns chandeliers
    sig_fast_candle = c_fast.replace(".csv", "_sig_candle.csv")
    sig_slow_candle = c_slow.replace(".csv", "_sig_candle.csv")
    step_patterns(c_fast, sig_fast_candle)
    step_patterns(c_slow, sig_slow_candle)

    # 5) features microstructure (alignées au pas)
    m_fast = f"data/{args.pair.replace('/','_').lower()}_micro_{args.dt_fast}s.csv"
    m_slow = f"data/{args.pair.replace('/','_').lower()}_micro_{args.dt_slow}s.csv"
    step_micro_features(topbook_csv, m_fast, args.dt_fast)
    step_micro_features(topbook_csv, m_slow, args.dt_slow)

    # 6) signal micro
    sig_fast_micro = c_fast.replace(".csv", "_sig_micro.csv")
    sig_slow_micro = c_slow.replace(".csv", "_sig_micro.csv")
    step_micro_signal(m_fast, sig_fast_micro, args.tau, args.max_spread_bp)
    step_micro_signal(m_slow, sig_slow_micro, args.tau, args.max_spread_bp)

    # 7) backtests
    bt_fast_candle = c_fast.replace(".csv", "_bt_candle.csv")
    bt_slow_candle = c_slow.replace(".csv", "_bt_candle.csv")
    bt_fast_micro  = c_fast.replace(".csv", "_bt_micro.csv")
    bt_slow_micro  = c_slow.replace(".csv", "_bt_micro.csv")

    step_backtest(c_fast_lbl, sig_fast_candle, m_fast, bt_fast_candle, args.h, args.fees_bp, tag="candle 5s")
    step_backtest(c_slow_lbl, sig_slow_candle, m_slow, bt_slow_candle, args.h, args.fees_bp, tag="candle 60s")
    step_backtest(c_fast_lbl, sig_fast_micro,  m_fast, bt_fast_micro,  args.h, args.fees_bp, tag="micro 5s")
    step_backtest(c_slow_lbl, sig_slow_micro,  m_slow, bt_slow_micro,  args.h, args.fees_bp, tag="micro 60s")

    print("\n[done]")
    print(f"- Candles: {c_fast}, {c_slow}")
    print(f"- Labels:  {c_fast_lbl}, {c_slow_lbl}")
    print(f"- Signals: {sig_fast_candle}, {sig_slow_candle}, {sig_fast_micro}, {sig_slow_micro}")
    print(f"- Micro:   {m_fast}, {m_slow}")
    print(f"- BT:      {bt_fast_candle}, {bt_slow_candle}, {bt_fast_micro}, {bt_slow_micro}")

if __name__ == "__main__":
    main()
