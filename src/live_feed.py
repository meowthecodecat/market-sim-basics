"""
Live Kraken market data feed utilities (trades + top-of-book) for the dashboard.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List, Optional

import pandas as pd
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

WS_URL = "wss://ws.kraken.com/v2"

def _parse_ts(value) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    try:
        return pd.to_datetime(value, utc=True, errors="coerce").to_pydatetime()
    except Exception:
        return datetime.now(timezone.utc)

def _apply_levels(levels: Dict[float, float], updates: Optional[List[Dict[str, str]]]) -> None:
    if not updates:
        return
    for item in updates:
        price = float(item["price"])
        qty = float(item["qty"])
        if qty <= 0.0:
            levels.pop(price, None)
        else:
            levels[price] = qty

def _best(levels: Dict[float, float], side: str) -> tuple[Optional[float], Optional[float]]:
    if not levels:
        return None, None
    price = max(levels) if side == "bid" else min(levels)
    return price, levels.get(price)

@dataclass
class BookSnapshot:
    timestamp: datetime
    bid_px: Optional[float]
    bid_qty: Optional[float]
    ask_px: Optional[float]
    ask_qty: Optional[float]
    mid: Optional[float]
    spread: Optional[float]

class KrakenLiveFeed:
    """
    Maintains a live websocket connection to Kraken and stores recent trades plus top-of-book data.
    """

    def __init__(
        self,
        pair: str = "BTC/USD",
        depth: int = 25,
        history_hours: float = 48.0,
        log_every: float = 30.0,
    ) -> None:
        self.pair = pair
        self.depth = depth
        self.log_every = log_every
        self.max_age = timedelta(hours=history_hours)

        self._trades: Deque[Dict[str, float]] = deque()
        self._lock = threading.Lock()
        self._book_snapshot: Optional[BookSnapshot] = None
        self._status: str = "init"
        self._first_mid: Optional[float] = None
        self._first_mid_ts: Optional[datetime] = None
        self._last_mid: Optional[float] = None
        self._last_mid_ts: Optional[datetime] = None

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_background, daemon=True)
        self._thread.start()

    # === public API =======================================================

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def is_running(self) -> bool:
        return self._thread.is_alive() and not self._stop_event.is_set()

    def status(self) -> str:
        return self._status

    def latest_trade(self) -> Optional[Dict[str, float]]:
        with self._lock:
            return self._trades[-1] if self._trades else None

    def get_trades_df(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        with self._lock:
            if not self._trades:
                return pd.DataFrame(columns=["timestamp", "price", "qty", "side"])
            data = list(self._trades)
        if max_rows is not None:
            data = data[-max_rows:]
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    def get_book_snapshot(self) -> Optional[BookSnapshot]:
        return self._book_snapshot

    def price_metrics(self) -> dict:
        with self._lock:
            return {
                "last_mid": self._last_mid,
                "last_mid_ts": self._last_mid_ts.isoformat() if self._last_mid_ts else None,
                "first_mid": self._first_mid,
                "first_mid_ts": self._first_mid_ts.isoformat() if self._first_mid_ts else None,
            }

    # === internal logic ===================================================

    def _run_background(self) -> None:
        try:
            asyncio.run(self._loop())
        except Exception as exc:
            self._status = f"loop_error: {exc}"

    async def _loop(self) -> None:
        backoff = 1.0
        while not self._stop_event.is_set():
            try:
                await self._stream_once()
                backoff = 1.0
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as exc:
                self._status = f"disconnected: {type(exc).__name__}"
            except asyncio.TimeoutError:
                self._status = "timeout"
            except Exception as exc:
                self._status = f"error: {exc}"
            if self._stop_event.is_set():
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    async def _stream_once(self) -> None:
        self._status = "connecting"
        bids: Dict[float, float] = {}
        asks: Dict[float, float] = {}
        n_trade = 0
        n_book = 0
        loop = asyncio.get_event_loop()
        last_log = loop.time()

        async with websockets.connect(
            WS_URL,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        ) as ws:
            await ws.send(json.dumps({"method": "subscribe", "params": {"channel": "trade", "symbol": [self.pair]}}))
            await ws.send(json.dumps({"method": "subscribe", "params": {"channel": "book", "symbol": [self.pair], "depth": self.depth, "snapshot": True}}))
            self._status = "streaming"

            while not self._stop_event.is_set():
                raw = await ws.recv()
                data = json.loads(raw)
                channel = data.get("channel")

                if channel == "trade":
                    for tr in data.get("data", []):
                        self._handle_trade(tr)
                        n_trade += 1
                elif channel == "book":
                    payload_list = data.get("data") or [{}]
                    payload = payload_list[0] if payload_list else {}
                    typ = data.get("type")
                    if typ == "snapshot":
                        bids.clear()
                        asks.clear()
                        for b in payload.get("bids") or []:
                            bids[float(b["price"])] = float(b["qty"])
                        for a in payload.get("asks") or []:
                            asks[float(a["price"])] = float(a["qty"])
                    elif typ == "update":
                        _apply_levels(bids, payload.get("bids"))
                        _apply_levels(asks, payload.get("asks"))

                    bid_px, bid_qty = _best(bids, "bid")
                    ask_px, ask_qty = _best(asks, "ask")
                    if bid_px is not None and ask_px is not None:
                        mid = (bid_px + ask_px) / 2.0
                        spread = max(ask_px - bid_px, 0.0)
                    else:
                        mid = spread = None

                    self._book_snapshot = BookSnapshot(
                        timestamp=datetime.now(timezone.utc),
                        bid_px=bid_px,
                        bid_qty=bid_qty,
                        ask_px=ask_px,
                        ask_qty=ask_qty,
                        mid=mid,
                        spread=spread,
                    )
                    n_book += 1
                    if mid is not None:
                        now_ts = datetime.now(timezone.utc)
                        with self._lock:
                            if self._first_mid is None:
                                self._first_mid = mid
                                self._first_mid_ts = now_ts
                            self._last_mid = mid
                            self._last_mid_ts = now_ts

                now = loop.time()
                if now - last_log >= self.log_every:
                    self._status = f"streaming trades={n_trade} book_updates={n_book}"
                    last_log = now

    def _handle_trade(self, tr: Dict[str, str]) -> None:
        ts = _parse_ts(tr.get("timestamp"))
        record = {
            "timestamp": ts,
            "price": float(tr.get("price", 0.0)),
            "qty": float(tr.get("qty", 0.0)),
            "side": tr.get("side"),
        }
        with self._lock:
            self._trades.append(record)
            self._trim_trades_locked()

    def _trim_trades_locked(self) -> None:
        if not self._trades:
            return
        cutoff = datetime.now(timezone.utc) - self.max_age
        while self._trades and self._trades[0]["timestamp"] < cutoff:
            self._trades.popleft()
