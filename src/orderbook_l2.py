# src/crypto/orderbook_l2.py
from __future__ import annotations
from typing import Dict, Tuple, List, Literal, Optional
from dataclasses import dataclass

Side = Literal["bids", "asks"]

@dataclass
class Level:
    price: float
    qty: float

class L2Book:
    def __init__(self, depth: int = 25) -> None:
        assert depth in (10,25,100,500,1000)
        self.depth = depth
        self.bids: Dict[float, float] = {}  # price -> qty
        self.asks: Dict[float, float] = {}

    def reset_snapshot(self, bids: List[dict], asks: List[dict]) -> None:
        self.bids.clear(); self.asks.clear()
        for lv in bids: self._set("bids", float(lv["price"]), float(lv["qty"]))
        for lv in asks: self._set("asks", float(lv["price"]), float(lv["qty"]))
        self._trim()

    def apply_update(self, bids: List[dict], asks: List[dict]) -> None:
        for lv in bids: self._set("bids", float(lv["price"]), float(lv["qty"]))
        for lv in asks: self._set("asks", float(lv["price"]), float(lv["qty"]))
        self._gc_zero()
        self._trim()

    def best(self) -> Tuple[Optional[Tuple[float,float]], Optional[Tuple[float,float]]]:
        bid = max(self.bids.items(), key=lambda x: x[0]) if self.bids else None
        ask = min(self.asks.items(), key=lambda x: x[0]) if self.asks else None
        return bid, ask

    def depth_qty(self, side: Side, top_n: int) -> float:
        book = self.bids if side == "bids" else self.asks
        prices = sorted(book.keys(), reverse=(side=="bids"))
        qty = 0.0
        for px in prices[:top_n]:
            qty += book[px]
        return qty

    def _set(self, side: Side, price: float, qty: float) -> None:
        book = self.bids if side == "bids" else self.asks
        if qty <= 0.0:
            book.pop(price, None)
        else:
            book[price] = qty

    def _gc_zero(self) -> None:
        for m in (self.bids, self.asks):
            for px in list(m.keys()):
                if m[px] <= 0.0:
                    m.pop(px, None)

    def _trim(self) -> None:
        # garde uniquement la profondeur demandée côté bid/ask
        if self.bids:
            bids_sorted = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:self.depth]
            self.bids = dict(bids_sorted)
        if self.asks:
            asks_sorted = sorted(self.asks.items(), key=lambda x: x[0])[:self.depth]
            self.asks = dict(asks_sorted)
