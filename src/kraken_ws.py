import asyncio, json, csv, argparse, os
from pathlib import Path
from datetime import datetime, timezone
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

WS_URL = "wss://ws.kraken.com/v2"

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def _apply(levels_map, updates):
    for u in updates or []:
        px = float(u["price"]); q = float(u["qty"])
        if q <= 0.0:
            levels_map.pop(px, None)
        else:
            levels_map[px] = q

def _best(levels_map, side):
    if not levels_map:
        return None, None
    px = max(levels_map) if side == "bid" else min(levels_map)
    return px, levels_map[px]

def _depth_sum(levels_map, side, topn=10):
    if not levels_map:
        return 0.0
    prices = sorted(levels_map, reverse=(side=="bid"))
    return float(sum(levels_map[p] for p in prices[:topn]))

def _csv_writer(path, header):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    file_exists = Path(path).exists() and Path(path).stat().st_size > 0
    f = open(path, "a", newline="", buffering=1)
    w = csv.writer(f)
    if not file_exists:
        w.writerow(header)
    return f, w

async def _stream_once(pair, depth, tw, bw, log_every):
    bids, asks = {}, {}
    n_trade = 0
    n_book = 0
    loop = asyncio.get_event_loop()
    last_log = loop.time()

    async with websockets.connect(
        WS_URL,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=5
    ) as ws:
        # Abonnements
        await ws.send(json.dumps({"method":"subscribe","params":{"channel":"trade","symbol":[pair]}}))
        await ws.send(json.dumps({"method":"subscribe","params":{"channel":"book","symbol":[pair],"depth":depth,"snapshot":True}}))
        print(f"[ws] connecté pair={pair} depth={depth}")

        while True:
            raw = await ws.recv()                 # peut lever ConnectionClosed*
            data = json.loads(raw)
            ch = data.get("channel")

            if ch == "trade":
                for tr in data.get("data", []):
                    ts = tr.get("timestamp") or iso_now()
                    sym = tr.get("symbol", pair)
                    side = tr.get("side")
                    price = float(tr.get("price", 0.0))
                    qty = float(tr.get("qty", 0.0))
                    ord_type = tr.get("ord_type")
                    tid = tr.get("trade_id")
                    tw.writerow([ts, sym, side, f"{price:.2f}", f"{qty:.8f}", ord_type, tid])
                    n_trade += 1

            elif ch == "book":
                typ = data.get("type")
                payload = (data.get("data") or [{}])[0]
                sym = payload.get("symbol", pair)

                if typ == "snapshot":
                    bids.clear(); asks.clear()
                    for b in payload.get("bids") or []:
                        bids[float(b["price"])] = float(b["qty"])
                    for a in payload.get("asks") or []:
                        asks[float(a["price"])] = float(a["qty"])
                elif typ == "update":
                    _apply(bids, payload.get("bids"))
                    _apply(asks, payload.get("asks"))

                bid_px, bid_qty = _best(bids, "bid")
                ask_px, ask_qty = _best(asks, "ask")
                if bid_px is not None and ask_px is not None:
                    mid = (bid_px + ask_px)/2.0
                    spread = ask_px - bid_px
                    bd = _depth_sum(bids, "bid", topn=10)
                    ad = _depth_sum(asks, "ask", topn=10)
                    bw.writerow([iso_now(), sym,
                                 f"{bid_px:.2f}", f"{(bid_qty or 0.0):.8f}",
                                 f"{ask_px:.2f}", f"{(ask_qty or 0.0):.8f}",
                                 f"{mid:.2f}", f"{spread:.2f}",
                                 f"{bd:.8f}", f"{ad:.8f}"])
                    n_book += 1

            # log périodique
            now = loop.time()
            if now - last_log >= log_every:
                print(f"[ws] trades={n_trade} book_updates={n_book}")
                last_log = now

async def run_ws(pair, depth, out_trades, out_topbook, log_every=10, max_backoff=60):
    # writers en append pour survivre aux reconnexions
    ft, tw = _csv_writer(out_trades,  ["timestamp","symbol","side","price","qty","ord_type","trade_id"])
    fb, bw = _csv_writer(out_topbook, ["timestamp","symbol","bid_px","bid_qty","ask_px","ask_qty","mid","spread","bid_depth_qty","ask_depth_qty"])
    backoff = 1
    try:
        while True:
            try:
                await _stream_once(pair, depth, tw, bw, log_every)
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
                print(f"[ws] déconnecté: {type(e).__name__} → reconnexion dans {backoff}s")
            except asyncio.TimeoutError:
                print(f"[ws] timeout → reconnexion dans {backoff}s")
            except Exception as e:
                print(f"[ws] erreur: {e} → reconnexion dans {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)  # backoff exponentiel
    finally:
        ft.close(); fb.close()

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", type=str, default="BTC/USD")
    ap.add_argument("--depth", type=int, default=25)
    ap.add_argument("--out_trades", type=str, default="data/kraken_trades.csv")
    ap.add_argument("--out_topbook", type=str, default="data/kraken_topbook.csv")
    ap.add_argument("--log_every", type=int, default=10)
    return ap.parse_args()

def main():
    a = parse_args()
    try:
        asyncio.run(run_ws(a.pair, a.depth, a.out_trades, a.out_topbook, a.log_every))
    except KeyboardInterrupt:
        print("\n[ws] arrêté")

if __name__ == "__main__":
    main()
