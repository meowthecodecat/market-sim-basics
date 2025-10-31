"""
Simple portfolio simulator that consumes candle + signal streams.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

@dataclass
class TradeEvent:
    t0: str
    price: float
    action: str  # buy / sell / short / cover
    qty: float
    cash: float
    equity: float

@dataclass
class EquityPoint:
    t0: str
    price: float
    signal: int
    position: float
    cash: float
    equity: float
    unrealized: float
    realized: float
    action: str

@dataclass
class TradingSimulator:
    initial_cash: float = 100.0
    allow_short: bool = False
    fee_bps: float = 0.0
    history: List[EquityPoint] = field(default_factory=list)
    trades: List[TradeEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.cash = float(self.initial_cash)
        self.position = 0.0  # BTC quantity (positive long, negative short)
        self.avg_entry_price: Optional[float] = None
        self.history = []
        self.trades = []
        self._last_price: Optional[float] = None

    @property
    def last_equity(self) -> Optional[float]:
        if not self.history:
            return None
        return self.history[-1].equity

    def current_equity(self, price: Optional[float] = None) -> float:
        px = price if price is not None else (self._last_price or 0.0)
        return self.cash + self.position * px

    def _apply_fees(self, qty: float, price: float) -> float:
        if self.fee_bps <= 0:
            return 0.0
        fee = qty * price * (self.fee_bps * 1e-4)
        self.cash -= fee
        return fee

    def _trade_capacity(self, price: float) -> float:
        if price <= 0:
            return 0.0
        if self.fee_bps > 0:
            fee_factor = 1 + (self.fee_bps * 1e-4)
        else:
            fee_factor = 1.0
        return self.cash / (price * fee_factor) if self.cash > 0 else 0.0

    def on_candle(self, row: pd.Series, signal: int) -> None:
        price = float(row["close"])
        t0 = row.get("t0")
        if pd.isna(price) or price <= 0:
            return

        action = "hold"
        qty = 0.0

        if signal > 0:
            # Close short if any
            if self.position < 0:
                qty = abs(self.position)
                if qty > 0:
                    self._apply_fees(qty, price)
                    self.cash -= qty * price
                    self.position = 0.0
                    action = "buy_to_cover"
                    self.avg_entry_price = None
                    self._record_trade(t0, price, action, qty)
            # Open long if flat and cash available
            if self.position == 0 and self.cash > 0:
                qty = self._trade_capacity(price)
                if qty > 0:
                    self._apply_fees(qty, price)
                    self.cash -= qty * price
                    self.position += qty
                    self.avg_entry_price = price
                    action = "buy"
                    self._record_trade(t0, price, action, qty)

        elif signal < 0:
            # Close long if any
            if self.position > 0:
                qty = self.position
                self.cash += qty * price
                self._apply_fees(qty, price)
                self.position = 0.0
                self.avg_entry_price = None
                action = "sell"
                self._record_trade(t0, price, action, qty)
            elif self.allow_short and self.cash > 0:
                qty = self._trade_capacity(price)
                if qty > 0:
                    self._apply_fees(qty, price)
                    self.position -= qty
                    self.cash += qty * price
                    self.avg_entry_price = price
                    action = "short"
                    self._record_trade(t0, price, action, qty)

        equity = self.current_equity(price)
        unrealized = 0.0
        if self.position != 0 and self.avg_entry_price is not None:
            unrealized = (price - self.avg_entry_price) * self.position
        realized = equity - unrealized - self.initial_cash

        self.history.append(EquityPoint(
            t0=str(t0),
            price=price,
            signal=int(signal),
            position=self.position,
            cash=self.cash,
            equity=equity,
            unrealized=unrealized,
            realized=realized,
            action=action,
        ))
        self._last_price = price

    def _record_trade(self, t0: str, price: float, action: str, qty: float) -> None:
        self.trades.append(TradeEvent(
            t0=str(t0),
            price=price,
            action=action,
            qty=qty,
            cash=self.cash,
            equity=self.current_equity(price),
        ))

    def history_df(self) -> pd.DataFrame:
        if not self.history:
            return pd.DataFrame(columns=[
                "t0", "price", "signal", "position", "cash", "equity", "unrealized", "realized", "action"
            ])
        return pd.DataFrame([h.__dict__ for h in self.history])

    def trades_df(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(columns=["t0", "price", "action", "qty", "cash", "equity"])
        return pd.DataFrame([t.__dict__ for t in self.trades])

    def summary(self) -> dict:
        price = self._last_price
        if price is None:
            price = self.avg_entry_price if self.avg_entry_price is not None else 0.0
        equity = self.current_equity(price)
        unrealized = 0.0
        if self.position != 0 and self.avg_entry_price is not None:
            unrealized = (price - self.avg_entry_price) * self.position
        realized = equity - unrealized - self.initial_cash
        pnl_total = equity - self.initial_cash
        pct_total = (pnl_total / self.initial_cash) * 100 if self.initial_cash else 0.0
        pct_realized = (realized / self.initial_cash) * 100 if self.initial_cash else 0.0
        pct_unrealized = (unrealized / self.initial_cash) * 100 if self.initial_cash else 0.0
        return {
            "initial_cash": self.initial_cash,
            "equity": equity,
            "pnl": pnl_total,
            "pnl_pct": pct_total,
            "pnl_realized": realized,
            "pnl_realized_pct": pct_realized,
            "pnl_unrealized": unrealized,
            "pnl_unrealized_pct": pct_unrealized,
            "n_trades": len(self.trades),
        }
