"""
FastAPI server providing a live simulation of the Kraken-based trading bot.

It exposes REST endpoints to:
  - Inspect current status and config.
  - Retrieve recent candles + pattern detections.
  - Monitor bot equity and executed trades.
  - Reset or reconfigure the simulator on the fly.

Run with:
  uvicorn src.server:app --reload
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set, Tuple

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .candles import aggregate_trades_df
from .live_feed import KrakenLiveFeed
from .patterns_candles import compute_pattern_indicators
from .simulator import TradingSimulator

DEFAULT_PAIR = "BTC/USD"
DEFAULT_CANDLE_SEC = 60
DEFAULT_INITIAL_CASH = 100.0
DEFAULT_ALLOW_SHORT = False
DEFAULT_FEE_BPS = 5.0
PROCESS_INTERVAL_SEC = 1
MAX_PROCESSED_KEYS = 20_000

class ConfigPayload(BaseModel):
    pair: Optional[str] = None
    candle_sec: Optional[int] = None
    initial_cash: Optional[float] = None
    allow_short: Optional[bool] = None
    fee_bps: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_hold_candles: Optional[int] = None
    trailing_stop_pct: Optional[float] = None
    position_scale: Optional[float] = None
    max_leverage: Optional[float] = None

@dataclass
class Snapshot:
    candles: pd.DataFrame
    history: pd.DataFrame
    trades: pd.DataFrame
    summary: dict
    last_update: Optional[datetime]

class LiveSimulationState:
    """
    Aggregates Kraken trades into candles, runs the pattern detectors,
    and updates a trading simulator in the background.
    """

    def __init__(
        self,
        pair: str = DEFAULT_PAIR,
        candle_sec: int = DEFAULT_CANDLE_SEC,
        initial_cash: float = DEFAULT_INITIAL_CASH,
        allow_short: bool = DEFAULT_ALLOW_SHORT,
        fee_bps: float = DEFAULT_FEE_BPS,
        process_interval: int = PROCESS_INTERVAL_SEC,
        stop_loss_pct: Optional[float] = 0.01,
        take_profit_pct: Optional[float] = 0.02,
        max_hold_candles: Optional[int] = 180,
        trailing_stop_pct: Optional[float] = 0.01,
        position_scale: float = 1.0,
        max_leverage: float = 1.0,
    ) -> None:
        self.lock = threading.Lock()
        self.process_interval = process_interval

        self.feed_pair = pair
        self.candle_sec = candle_sec
        self.initial_cash = initial_cash
        self.allow_short = allow_short
        self.fee_bps = fee_bps
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_hold_candles = max_hold_candles
        self.trailing_stop_pct = trailing_stop_pct if trailing_stop_pct and trailing_stop_pct > 0 else None
        self.position_scale = max(0.2, min(2.0, position_scale)) if position_scale else 1.0
        self.max_leverage = max(1.0, float(max_leverage)) if max_leverage else 1.0

        self.feed = KrakenLiveFeed(pair=pair)
        self.simulator = TradingSimulator(
            initial_cash=initial_cash,
            allow_short=allow_short,
            fee_bps=fee_bps,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            trailing_stop_pct=self.trailing_stop_pct,
            max_holding_period=max_hold_candles,
            position_scale=self.position_scale,
            max_leverage=self.max_leverage,
        )
        self.processed_keys: Set[str] = set()
        self.candles_df = pd.DataFrame(columns=["t0", "open", "high", "low", "close", "volume"])
        self.history_df = pd.DataFrame()
        self.trades_df = pd.DataFrame()
        self.summary = self.simulator.summary()
        self.last_update: Optional[datetime] = None

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self.last_price: Optional[float] = None
        self.price_change_pct: Optional[float] = None
        self.price_timestamp: Optional[datetime] = None
        self.price_reference: Optional[float] = None
        self.price_reference_ts: Optional[datetime] = None
        self.latest_market_metrics: Optional[dict] = None

    # === background management ===========================================

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_loop())

    async def shutdown(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.feed.stop()

    async def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                self._step()
                await asyncio.sleep(self.process_interval)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            # store the exception in status for observability
            with self.lock:
                self.summary["error"] = str(exc)

    # === core processing =================================================

    def _step(self) -> None:
        trades_df = self.feed.get_trades_df()
        if trades_df.empty:
            return

        candles_input = trades_df.rename(columns={"qty": "volume"})
        candles_df = aggregate_trades_df(candles_input, self.candle_sec)
        if candles_df.empty:
            return

        indicators = compute_pattern_indicators(candles_df[["open", "high", "low", "close"]])
        candles_df = pd.concat([candles_df, indicators], axis=1)

        market_metrics_latest = self.feed.get_market_metrics(1).get("latest")
        self.latest_market_metrics = market_metrics_latest
        micro_signal, micro_score = self._micro_signal_from_metrics(market_metrics_latest)

        new_keys = []
        for idx, row in candles_df.iterrows():
            key = row["t0"]
            if key in self.processed_keys:
                continue
            signal = int(row.get("signal_candle", 0))
            combined_signal = signal
            if micro_signal:
                if combined_signal == 0:
                    combined_signal = micro_signal
                else:
                    mix = combined_signal + micro_signal
                    if mix > 0:
                        combined_signal = 1
                    elif mix < 0:
                        combined_signal = -1
            enriched_row = row.copy()
            enriched_row["signal_micro_live"] = micro_signal
            enriched_row["micro_score"] = micro_score
            if market_metrics_latest:
                enriched_row["depth_imb_live"] = market_metrics_latest.get("depth_imbalance")
                enriched_row["spread_bp_live"] = market_metrics_latest.get("spread_bp")
            candles_df.at[idx, "signal_micro_live"] = micro_signal
            candles_df.at[idx, "micro_score"] = micro_score
            candles_df.at[idx, "signal_combined"] = combined_signal
            if market_metrics_latest:
                candles_df.at[idx, "depth_imb_live"] = market_metrics_latest.get("depth_imbalance")
                candles_df.at[idx, "spread_bp_live"] = market_metrics_latest.get("spread_bp")
            self.simulator.on_candle(enriched_row, combined_signal)
            self.processed_keys.add(key)
            new_keys.append(key)

        if new_keys:
            # keep processed keys bounded
            if len(self.processed_keys) > MAX_PROCESSED_KEYS:
                sorted_keys = sorted(self.processed_keys)
                trim = len(self.processed_keys) - MAX_PROCESSED_KEYS
                for key in sorted_keys[:trim]:
                    self.processed_keys.discard(key)

        with self.lock:
            self.candles_df = candles_df
            self.history_df = self.simulator.history_df()
            self.trades_df = self.simulator.trades_df()
            self.summary = self.simulator.summary()
            self.summary["feed_status"] = self.feed.status()
            self.summary["feed_running"] = self.feed.is_running()
            self.summary["pair"] = self.feed_pair
            self.summary["candle_sec"] = self.candle_sec
            if self.latest_market_metrics:
                self.summary["market_latency_ms"] = self.latest_market_metrics.get("latency_ms")
                self.summary["depth_imbalance"] = self.latest_market_metrics.get("depth_imbalance")
                self.summary["spread_bp"] = self.latest_market_metrics.get("spread_bp")
            self.last_update = datetime.now(timezone.utc)
            price_info = self.feed.price_metrics()
            self.last_price = price_info.get("last_mid")
            self.price_timestamp = (
                datetime.fromisoformat(price_info["last_mid_ts"])
                if price_info.get("last_mid_ts")
                else None
            )
            first_mid = price_info.get("first_mid")
            first_mid_ts = price_info.get("first_mid_ts")
            self.price_reference = first_mid
            self.price_reference_ts = (
                datetime.fromisoformat(first_mid_ts) if first_mid_ts else None
            )
            if self.last_price is not None and first_mid:
                self.price_change_pct = ((self.last_price / first_mid) - 1.0) * 100.0
            else:
                self.price_change_pct = None
            self.summary["price_last"] = self.last_price
            self.summary["price_change_pct"] = self.price_change_pct
            self.summary["price_timestamp"] = (
                self.price_timestamp.isoformat() if self.price_timestamp else None
            )
            self.summary["price_reference"] = self.price_reference
            self.summary["price_reference_ts"] = (
                self.price_reference_ts.isoformat() if self.price_reference_ts else None
            )

    # === public helpers ==================================================

    def snapshot(self) -> Snapshot:
        with self.lock:
            return Snapshot(
                candles=self.candles_df.copy(),
                history=self.history_df.copy(),
                trades=self.trades_df.copy(),
                summary=self.summary.copy(),
                last_update=self.last_update,
            )

    def order_book(self, depth: int) -> dict:
        depth = max(1, depth)
        feed_depth = getattr(self.feed, "depth", depth)
        if feed_depth:
            depth = min(depth, int(feed_depth))
        ob = self.feed.get_order_book(depth)
        ts = ob.get("timestamp")
        return {
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else ts,
            "bids": ob.get("bids", []),
            "asks": ob.get("asks", []),
            "latency_ms": ob.get("latency_ms"),
        }

    def market_metrics(self, history: int = 120) -> dict:
        history = max(1, history)
        metrics = self.feed.get_market_metrics(history)
        latest = metrics.get("latest")
        if latest:
            self.latest_market_metrics = latest
        return metrics

    def logs(self, limit: int = 200) -> List[dict]:
        limit = max(1, min(limit, self.simulator.max_debug_entries))
        return self.simulator.logs(limit)

    def _micro_signal_from_metrics(self, metrics: Optional[dict]) -> tuple[int, float]:
        if not metrics:
            return 0, 0.0
        depth_imb = metrics.get("depth_imbalance")
        if depth_imb is None:
            return 0, 0.0
        spread_bp = metrics.get("spread_bp") or 0.0
        volatility = metrics.get("volatility") or 0.0
        adaptive_tau = max(
            0.02,
            min(
                0.35,
                0.06
                + (volatility * 2.5)
                + (abs(spread_bp) * 0.0015),
            ),
        )
        score = depth_imb
        if abs(score) > adaptive_tau:
            return (1 if score > 0 else -1), score
        return 0, score

    def update_config(self, payload: ConfigPayload) -> None:
        reinit_sim = False
        restart_feed = False

        if payload.pair and payload.pair != self.feed_pair:
            self.feed.stop()
            self.feed_pair = payload.pair
            self.feed = KrakenLiveFeed(pair=self.feed_pair)
            restart_feed = True

        if payload.candle_sec and payload.candle_sec != self.candle_sec:
            self.candle_sec = payload.candle_sec
            # Reset processed keys so the simulator replays candles with new resolution
            self.processed_keys.clear()
            reinit_sim = True

        if payload.initial_cash is not None and payload.initial_cash != self.initial_cash:
            self.initial_cash = payload.initial_cash
            reinit_sim = True
        if payload.allow_short is not None and payload.allow_short != self.allow_short:
            self.allow_short = payload.allow_short
            reinit_sim = True
        if payload.fee_bps is not None and payload.fee_bps != self.fee_bps:
            self.fee_bps = payload.fee_bps
            reinit_sim = True
        if payload.stop_loss_pct is not None:
            self.stop_loss_pct = max(0.0, payload.stop_loss_pct)
            reinit_sim = True
        if payload.take_profit_pct is not None:
            self.take_profit_pct = max(0.0, payload.take_profit_pct)
            reinit_sim = True
        if payload.max_hold_candles is not None:
            self.max_hold_candles = max(1, int(payload.max_hold_candles))
            reinit_sim = True
        if payload.trailing_stop_pct is not None:
            self.trailing_stop_pct = payload.trailing_stop_pct if payload.trailing_stop_pct and payload.trailing_stop_pct > 0 else None
            reinit_sim = True
        if payload.position_scale is not None:
            self.position_scale = max(0.2, min(2.0, float(payload.position_scale)))
            reinit_sim = True
        if payload.max_leverage is not None:
            self.max_leverage = max(1.0, float(payload.max_leverage))
            reinit_sim = True

        if reinit_sim:
            self.simulator = TradingSimulator(
                initial_cash=self.initial_cash,
                allow_short=self.allow_short,
                fee_bps=self.fee_bps,
                stop_loss_pct=self.stop_loss_pct,
                take_profit_pct=self.take_profit_pct,
                trailing_stop_pct=self.trailing_stop_pct,
                max_holding_period=self.max_hold_candles,
                position_scale=self.position_scale,
                max_leverage=self.max_leverage,
            )
            self.processed_keys.clear()

        if restart_feed and not self.feed.is_running():
            # give the feed a moment to reconnect
            pass

    def reset_simulation(self) -> None:
        self.simulator = TradingSimulator(
            initial_cash=self.initial_cash,
            allow_short=self.allow_short,
            fee_bps=self.fee_bps,
            stop_loss_pct=self.stop_loss_pct,
            take_profit_pct=self.take_profit_pct,
            trailing_stop_pct=self.trailing_stop_pct,
            max_holding_period=self.max_hold_candles,
            position_scale=self.position_scale,
            max_leverage=self.max_leverage,
        )
        self.processed_keys.clear()

app = FastAPI(title="Live BTC Bot Simulator", version="1.0")
STATE = LiveSimulationState()

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STATIC_BUILD_DIR = FRONTEND_DIR / "dist"
if STATIC_BUILD_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_BUILD_DIR, html=False), name="assets")
else:
    legacy_assets = FRONTEND_DIR if FRONTEND_DIR.exists() else None
    if legacy_assets:
        app.mount("/assets", StaticFiles(directory=legacy_assets, html=False), name="assets")

@app.on_event("startup")
async def _startup() -> None:
    STATE.start()

@app.on_event("shutdown")
async def _shutdown() -> None:
    await STATE.shutdown()

@app.get("/", response_class=FileResponse)
def root():
    index_path = STATIC_BUILD_DIR / "index.html"
    if not index_path.exists():
        index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend missing")
    return FileResponse(index_path)

@app.get("/status")
def get_status():
    snap = STATE.snapshot()
    data = snap.summary.copy()
    data["last_update"] = snap.last_update.isoformat() if snap.last_update else None
    data["last_price"] = STATE.last_price
    data["price_change_pct"] = STATE.price_change_pct
    data["price_timestamp"] = (
        STATE.price_timestamp.isoformat() if STATE.price_timestamp else None
    )
    data["price_reference"] = STATE.price_reference
    data["price_reference_ts"] = (
        STATE.price_reference_ts.isoformat() if STATE.price_reference_ts else None
    )
    metrics_latest = STATE.market_metrics(history=0).get("latest")
    data["market_metrics"] = metrics_latest
    if metrics_latest:
        data["market_latency_ms"] = metrics_latest.get("latency_ms")
    data["feed_status"] = STATE.feed.status()
    data["feed_running"] = STATE.feed.is_running()
    return data

@app.get("/candles")
def get_candles(limit: int = 200):
    snap = STATE.snapshot()
    candles = snap.candles.tail(limit)
    return {
        "limit": limit,
        "count": len(candles),
        "candles": candles.to_dict(orient="records"),
    }

@app.get("/equity")
def get_equity(limit: int = 500):
    snap = STATE.snapshot()
    history = snap.history.tail(limit)
    return {
        "limit": limit,
        "count": len(history),
        "equity": history.to_dict(orient="records"),
    }

@app.get("/market_metrics")
def get_market_metrics(history: int = 120):
    history = max(1, min(history, 600))
    return STATE.market_metrics(history)

@app.get("/orderbook")
def get_orderbook(depth: int = 15):
    return STATE.order_book(depth)

@app.get("/bot_trades")
def get_bot_trades(limit: int = 100):
    snap = STATE.snapshot()
    trades = snap.trades.tail(limit)
    return {
        "limit": limit,
        "count": len(trades),
        "trades": trades.to_dict(orient="records"),
    }

@app.get("/logs")
def get_logs(limit: int = 200):
    logs = STATE.logs(limit)
    return {
        "limit": limit,
        "count": len(logs),
        "logs": logs,
    }

@app.post("/reset")
def reset_bot():
    STATE.reset_simulation()
    return {"status": "reset"}

@dataclass
class ConfigSnapshot:
    pair: str
    candle_sec: int
    initial_cash: float
    allow_short: bool
    fee_bps: float
    stop_loss_pct: Optional[float]
    take_profit_pct: Optional[float]
    max_hold_candles: Optional[int]

def _current_config():
    return ConfigSnapshot(
        pair=STATE.feed_pair,
        candle_sec=STATE.candle_sec,
        initial_cash=STATE.initial_cash,
        allow_short=STATE.allow_short,
        fee_bps=STATE.fee_bps,
        stop_loss_pct=STATE.stop_loss_pct,
        take_profit_pct=STATE.take_profit_pct,
        max_hold_candles=STATE.max_hold_candles,
    )

@app.post("/config")
def update_config(payload: ConfigPayload):
    if payload.candle_sec is not None and payload.candle_sec < 1:
        raise HTTPException(status_code=400, detail="candle_sec doit être >= 1")
    if payload.initial_cash is not None and payload.initial_cash <= 0:
        raise HTTPException(status_code=400, detail="initial_cash doit être > 0")
    STATE.update_config(payload)
    return {"status": "ok", "config": asdict(_current_config())}

@app.get("/config")
def get_config():
    return asdict(_current_config())
