import { useEffect, useMemo, useRef, useState } from 'react';

const REFRESH_INTERVAL = 1500;

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }
  return res.json();
}

export default function useDashboardData(orderbookDepth) {
  const [status, setStatus] = useState(null);
  const [candles, setCandles] = useState([]);
  const [equity, setEquity] = useState([]);
  const [trades, setTrades] = useState([]);
  const [orderbook, setOrderbook] = useState({ bids: [], asks: [], timestamp: null, latency_ms: null });
  const [marketMetrics, setMarketMetrics] = useState({ latest: null, history: [] });
  const [error, setError] = useState(null);

  const lastSignalRef = useRef(null);
  const [signalEvent, setSignalEvent] = useState(null);

  useEffect(() => {
    let alive = true;

    const load = async () => {
      try {
        const results = await Promise.allSettled([
          fetchJson('/status'),
          fetchJson('/candles?limit=200'),
          fetchJson('/equity?limit=400'),
          fetchJson('/bot_trades?limit=200'),
          fetchJson(`/orderbook?depth=${orderbookDepth}`),
          fetchJson('/market_metrics?history=240'),
        ]);

        if (!alive) {
          return;
        }

        const [statusRes, candlesRes, equityRes, tradesRes, orderbookRes, marketRes] = results;

        if (statusRes.status === 'fulfilled') setStatus(statusRes.value);
        if (candlesRes.status === 'fulfilled') setCandles(candlesRes.value.candles ?? []);
        if (equityRes.status === 'fulfilled') setEquity(equityRes.value.equity ?? []);
        if (tradesRes.status === 'fulfilled') setTrades(tradesRes.value.trades ?? []);
        if (orderbookRes.status === 'fulfilled') {
          const ob = orderbookRes.value ?? {};
          setOrderbook({
            bids: ob.bids ?? [],
            asks: ob.asks ?? [],
            timestamp: ob.timestamp ?? null,
            latency_ms: ob.latency_ms ?? null,
          });
        }
        if (marketRes.status === 'fulfilled') setMarketMetrics(marketRes.value ?? { latest: null, history: [] });

        const rejected = results.filter((item) => item.status === 'rejected');
        if (rejected.length) {
          const [firstError] = rejected;
          const message = firstError.reason?.message ?? 'Une requete a echoue';
          setError(message);
        } else {
          setError(null);
        }
      } catch (err) {
        if (!alive) return;
        setError(err instanceof Error ? err.message : 'Erreur inattendue');
      }
    };

    load();
    const id = setInterval(load, REFRESH_INTERVAL);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [orderbookDepth]);

  const derived = useMemo(() => {
    const timeline = (candles ?? []).slice(-80).map((row) => ({
      time: row.t0,
      signal: Number(row.signal_combined ?? row.signal_candle ?? 0),
      price: Number(row.close ?? 0),
    }));

    const depthGauge = marketMetrics?.latest?.depth_imbalance ?? 0;
    const spreadBp = marketMetrics?.latest?.spread_bp ?? 0;
    const latencySeries = (marketMetrics?.history ?? []).map((entry) => ({
      time: entry.timestamp,
      value: entry.latency_ms ?? 0,
    }));

    const pnl = Number(status?.pnl ?? 0);
    const mood = pnl >= 0 ? 'positive' : 'negative';
    const moodIntensity = Math.min(1, Math.abs(pnl) / 50);

    const tradesWithPnl = trades.map((row) => ({ ...row, pnl: Number(row.pnl ?? 0) }));
    const bestTrade = tradesWithPnl.reduce((acc, t) => (t.pnl > (acc?.pnl ?? -Infinity) ? t : acc), null);
    const worstTrade = tradesWithPnl.reduce((acc, t) => (t.pnl < (acc?.pnl ?? Infinity) ? t : acc), null);

    const holdBaseline = (() => {
      if (!candles.length) return null;
      const first = Number(candles[0].open ?? candles[0].close ?? 0);
      const last = Number(candles[candles.length - 1].close ?? 0);
      if (!first || !last) return null;
      const pct = (last / first - 1) * 100;
      return { pct, pnl: (pct / 100) * (status?.initial_cash ?? 100) };
    })();

    const badges = [];
    if ((status?.n_trades ?? 0) >= 10) badges.push({ label: 'Trader aguerri', detail: `${status.n_trades} trades` });
    if ((status?.pnl ?? 0) > 0) badges.push({ label: 'PnL positif', detail: `+${status.pnl.toFixed(2)}` });
    if ((status?.hit_rate_last_20 ?? 0) > 0.6) {
      const pct = ((status.hit_rate_last_20 ?? 0) * 100).toFixed(1);
      badges.push({ label: 'Sniper', detail: `${pct}% hit` });
    }

    return {
      timeline,
      depthGauge,
      spreadBp,
      latencySeries,
      mood,
      moodIntensity,
      bestTrade,
      worstTrade,
      holdBaseline,
      badges,
    };
  }, [candles, trades, marketMetrics, status]);

  useEffect(() => {
    if (!derived.timeline?.length) return;
    const last = derived.timeline[derived.timeline.length - 1];
    if (last.signal && last.signal !== lastSignalRef.current) {
      lastSignalRef.current = last.signal;
      setSignalEvent({ time: last.time, signal: last.signal });
    }
  }, [derived.timeline]);

  return {
    status,
    candles,
    equity,
    trades,
    orderbook,
    marketMetrics,
    error,
    signalEvent,
    ...derived,
  };
}
