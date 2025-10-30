# src/crypto/kraken_ws.py
import asyncio, json, csv
from pathlib import Path
from datetime import datetime, timezone
import websockets
from .orderbook_l2 import L2Book

WS_URL = "wss://ws.kraken.com/v2"

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

async def stream(pair: str = "BTC/USD", depth: int = 25,
                 trades_csv: str = "data/kraken_trades.csv",
                 topbook_csv: str = "data/kraken_topbook.csv") -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    # prépare CSV
    t_file = open(trades_csv, "w", newline="")
    tb_file = open(topbook_csv, "w", newline="")
    t_w = csv.writer(t_file); t_w.writerow(["timestamp","symbol","side","price","qty","ord_type","trade_id"])
    tb_w = csv.writer(tb_file); tb_w.writerow(["timestamp","symbol","bid_px","bid_qty","ask_px","ask_qty","mid","spread","bid_depth_qty","ask_depth_qty"])

    book = L2Book(depth=depth)

    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
        # subscribe book
        sub_book = {"method":"subscribe","params":{"channel":"book","symbol":[pair],"depth":depth,"snapshot":True}}
        await ws.send(json.dumps(sub_book))
        # subscribe trades
        sub_trade = {"method":"subscribe","params":{"channel":"trade","symbol":[pair],"snapshot":False}}
        await ws.send(json.dumps(sub_trade))

        while True:
            raw = await ws.recv()
            msg = json.loads(raw)

            # Book L2
            if msg.get("channel") == "book":
                typ = msg.get("type")
                data = msg.get("data",[{}])[0]
                if typ == "snapshot":
                    book.reset_snapshot(bids=data.get("bids",[]), asks=data.get("asks",[]))
                elif typ == "update":
                    book.apply_update(bids=data.get("bids",[]), asks=data.get("asks",[]))
                # dump top-of-book à chaque update
                bid, ask = book.best()
                if bid and ask:
                    bid_px, bid_qty = bid; ask_px, ask_qty = ask
                    mid = (bid_px + ask_px) / 2.0
                    spread = ask_px - bid_px
                    tb_w.writerow([_iso_now(), data.get("symbol", pair), f"{bid_px:.2f}", f"{bid_qty:.8f}",
                                   f"{ask_px:.2f}", f"{ask_qty:.8f}", f"{mid:.2f}", f"{spread:.2f}",
                                   f"{book.depth_qty('bids', 10):.8f}", f"{book.depth_qty('asks', 10):.8f}"])
                    tb_file.flush()

            # Trades
            if msg.get("channel") == "trade":
                for tr in msg.get("data", []):
                    t_w.writerow([tr.get("timestamp"), tr.get("symbol", pair), tr.get("side"),
                                  f"{float(tr.get('price',0.0)):.2f}", f"{float(tr.get('qty',0.0)):.8f}",
                                  tr.get("ord_type"), tr.get("trade_id")])
                t_file.flush()
