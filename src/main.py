# src/main.py
import argparse
from pathlib import Path
from generator import generate_trades
from candles import build_candles
from plotter import plot_candles

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_trades", type=int, default=5000)
    ap.add_argument("--start_price", type=float, default=100.0)
    ap.add_argument("--volatility", type=float, default=0.002)
    ap.add_argument("--avg_volume", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dt", type=int, default=60, help="taille de bougie en secondes")
    ap.add_argument("--out_prefix", type=str, default="data/demo")
    ap.add_argument("--no_show", action="store_true", help="n’affiche pas les figures")
    return ap.parse_args()

def main():
    args = parse_args()
    trades_csv = f"{args.out_prefix}_trades.csv"
    candles_csv = f"{args.out_prefix}_candles_{args.dt}s.csv"
    png_prefix = f"{args.out_prefix}_{args.dt}s"

    # 1) Génération
    generate_trades(
        start_price=args.start_price,
        n_trades=args.n_trades,
        volatility=args.volatility,
        avg_volume=args.avg_volume,
        seed=args.seed,
        outfile=trades_csv,
    )

    # 2) Agrégation
    build_candles(trades_csv, candles_csv, args.dt)

    # 3) Affichage / export PNG
    plot_candles(candles_csv, save_prefix=png_prefix, show=not args.no_show)

    print(f"OK → {trades_csv} | {candles_csv} | {png_prefix}_price.png, {png_prefix}_volume.png")

if __name__ == "__main__":
    main()
