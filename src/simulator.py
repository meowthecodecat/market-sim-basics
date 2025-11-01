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
    pnl: float
    context: Optional[str] = None

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
    drawdown: float
    risk_event: Optional[str]
    position_age: int

@dataclass
class TradingSimulator:
    initial_cash: float = 100.0
    allow_short: bool = False
    fee_bps: float = 0.0
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    max_holding_period: Optional[int] = None
    position_scale: float = 1.0
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
        self.position_age = 0
        self._equity_peak = self.initial_cash
        self._max_drawdown = 0.0
        self._entry_high: Optional[float] = None
        self._entry_low: Optional[float] = None
        self._open_trade_equity: Optional[float] = None

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

    def _position_scale_from_row(self, row: pd.Series) -> float:
        base = max(0.1, min(1.0, self.position_scale))
        micro_strength = abs(float(row.get("micro_score", 0.0) or 0.0))
        mom_strength = abs(float(row.get("mom_signal", 0.0) or 0.0))
        raw = micro_strength * 0.7 + mom_strength * 0.3
        scale = max(base * 0.5, min(1.0, base * (0.4 + raw)))
        return scale

    def on_candle(self, row: pd.Series, signal: int) -> None:
        price = float(row["close"])
        t0 = row.get("t0")
        if pd.isna(price) or price <= 0:
            return

        action = "hold"
        qty = 0.0
        risk_event: Optional[str] = None
        risk_event_trigger: Optional[str] = None
        forced_signal: Optional[int] = None

        if self.position != 0:
            self.position_age += 1
        else:
            self.position_age = 0

        if self.position > 0:
            if self._entry_high is None:
                self._entry_high = price
            else:
                self._entry_high = max(self._entry_high, price)
        elif self.position < 0:
            if self._entry_low is None:
                self._entry_low = price
            else:
                self._entry_low = min(self._entry_low, price)
        else:
            self._entry_high = None
            self._entry_low = None

        if self.position != 0 and self.avg_entry_price not in (None, 0.0):
            if self.position > 0:
                ret = (price - self.avg_entry_price) / self.avg_entry_price
                if self.take_profit_pct and ret >= self.take_profit_pct:
                    forced_signal = -1
                    risk_event = "take_profit"
                elif self.stop_loss_pct and self.stop_loss_pct > 0 and ret <= -self.stop_loss_pct:
                    forced_signal = -1
                    risk_event = "stop_loss"
                elif self.trailing_stop_pct and self._entry_high:
                    trail = self._entry_high * (1 - self.trailing_stop_pct)
                    if price <= trail:
                        forced_signal = -1
                        risk_event = "trailing_stop"
            elif self.position < 0:
                ret = (self.avg_entry_price - price) / self.avg_entry_price
                if self.take_profit_pct and ret >= self.take_profit_pct:
                    forced_signal = 1
                    risk_event = "take_profit"
                elif self.stop_loss_pct and self.stop_loss_pct > 0 and ret <= -self.stop_loss_pct:
                    forced_signal = 1
                    risk_event = "stop_loss"
                elif self.trailing_stop_pct and self._entry_low:
                    trail = self._entry_low * (1 + self.trailing_stop_pct)
                    if price >= trail:
                        forced_signal = 1
                        risk_event = "trailing_stop"
        if (
            forced_signal is None
            and self.max_holding_period
            and self.position != 0
            and self.position_age >= self.max_holding_period
        ):
            forced_signal = -1 if self.position > 0 else 1
            risk_event = "max_hold"

        if forced_signal is not None:
            signal = forced_signal

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
                    trade_pnl = self.current_equity(price) - (self._open_trade_equity or self.current_equity(price))
                    self._record_trade(t0, price, action, qty, pnl=trade_pnl, context=risk_event)
                    risk_event_trigger = risk_event or risk_event_trigger
                    risk_event = None
                    self.position_age = 0
                    self._entry_low = None
                    self._open_trade_equity = None
            # Open long if flat and cash available
            if self.position == 0 and self.cash > 0:
                qty = self._trade_capacity(price) * self._position_scale_from_row(row)
                if qty > 0:
                    self._apply_fees(qty, price)
                    self.cash -= qty * price
                    self.position += qty
                    self.avg_entry_price = price
                    action = "buy"
                    self._record_trade(t0, price, action, qty, pnl=0.0)
                    self.position_age = 0
                    self._entry_high = price
                    self._open_trade_equity = self.current_equity(price)

        elif signal < 0:
            # Close long if any
            if self.position > 0:
                qty = self.position
                self.cash += qty * price
                self._apply_fees(qty, price)
                self.position = 0.0
                self.avg_entry_price = None
                action = "sell"
                trade_pnl = self.current_equity(price) - (self._open_trade_equity or self.current_equity(price))
                self._record_trade(t0, price, action, qty, pnl=trade_pnl, context=risk_event)
                risk_event_trigger = risk_event or risk_event_trigger
                risk_event = None
                self.position_age = 0
                self._entry_high = None
                self._open_trade_equity = None
            elif self.allow_short and self.cash > 0:
                qty = self._trade_capacity(price) * self._position_scale_from_row(row)
                if qty > 0:
                    self._apply_fees(qty, price)
                    self.position -= qty
                    self.cash += qty * price
                    self.avg_entry_price = price
                    action = "short"
                    self._record_trade(t0, price, action, qty, pnl=0.0)
                    self.position_age = 0
                    self._entry_low = price
                    self._open_trade_equity = self.current_equity(price)

        equity = self.current_equity(price)
        unrealized = 0.0
        if self.position != 0 and self.avg_entry_price is not None:
            unrealized = (price - self.avg_entry_price) * self.position
        realized = equity - unrealized - self.initial_cash
        if equity > self._equity_peak:
            self._equity_peak = equity
        drawdown = 0.0
        if self._equity_peak > 0:
            drawdown = (self._equity_peak - equity) / self._equity_peak
        if drawdown > self._max_drawdown:
            self._max_drawdown = drawdown

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
            drawdown=drawdown,
            risk_event=risk_event_trigger,
            position_age=self.position_age,
        ))
        self._last_price = price

    def _record_trade(
        self,
        t0: str,
        price: float,
        action: str,
        qty: float,
        pnl: float,
        context: Optional[str] = None,
    ) -> None:
        self.trades.append(TradeEvent(
            t0=str(t0),
            price=price,
            action=action,
            qty=qty,
            cash=self.cash,
            equity=self.current_equity(price),
             pnl=pnl,
            context=context,
        ))

    def history_df(self) -> pd.DataFrame:
        if not self.history:
            return pd.DataFrame(columns=[
                "t0", "price", "signal", "position", "cash", "equity",
                "unrealized", "realized", "action", "drawdown", "risk_event", "position_age"
            ])
        return pd.DataFrame([h.__dict__ for h in self.history])

    def trades_df(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(columns=["t0", "price", "action", "qty", "cash", "equity", "context"])
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
        max_drawdown_pct = self._max_drawdown * 100.0
        trades_df = self.trades_df()
        closing_trades = trades_df[trades_df["action"].isin(["sell", "buy_to_cover"])] if not trades_df.empty else pd.DataFrame()
        hit_last_20 = None
        pnl_last_20 = None
        avg_trade_pnl = None
        if not closing_trades.empty:
            recent = closing_trades.tail(20)
            hit_last_20 = float((recent["pnl"] > 0).mean()) if len(recent) else None
            pnl_last_20 = float(recent["pnl"].sum())
            avg_trade_pnl = float(closing_trades["pnl"].mean())
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
            "max_drawdown_pct": max_drawdown_pct,
            "position": self.position,
            "position_age": self.position_age,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "max_holding_period": self.max_holding_period,
            "hit_rate_last_20": hit_last_20,
            "pnl_last_20": pnl_last_20,
            "avg_trade_pnl": avg_trade_pnl,
        }
