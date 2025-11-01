import React from 'react';
import { useData } from '../../context/DataContext.jsx';
import MetricCard from './MetricCard.jsx';
import { fmtCurrency, fmtPercent, fmtLatency } from '../../utils/format.js';

export default function MetricGrid() {
  const { status, marketMetrics, holdBaseline } = useData();
  const latestSpread = marketMetrics?.latest?.spread_bp ?? null;
  const latestImbalance = marketMetrics?.latest?.depth_imbalance ?? null;
  const stopLossPct = Number(status?.stop_loss_pct ?? 0) * 100;
  const takeProfitPct = Number(status?.take_profit_pct ?? 0) * 100;
  const hitRatePct = status?.hit_rate_last_20 != null ? (status.hit_rate_last_20 * 100).toFixed(1) : null;
  const hitRateText = hitRatePct != null ? `${hitRatePct}%` : '--';

  const stats = [
    {
      label: 'Initial capital',
      value: fmtCurrency(status?.initial_cash),
      note: 'Base stake',
    },
    {
      label: 'Equity',
      value: fmtCurrency(status?.equity),
      note: `Trades ${status?.n_trades ?? 0}`,
    },
    {
      label: 'BTC/USD',
      value: status?.last_price ? fmtCurrency(status.last_price) : '--',
      note: `Updated ${status?.price_timestamp ? new Date(status.price_timestamp).toLocaleTimeString('fr-FR', { hour12: false }) : '--'}`,
    },
    {
      label: 'PnL (total)',
      value: fmtCurrency(status?.pnl),
      delta: fmtPercent(status?.pnl_pct),
      note: 'vs initial',
    },
    {
      label: 'PnL (realized)',
      value: fmtCurrency(status?.pnl_realized),
      delta: fmtPercent(status?.pnl_realized_pct),
      note: 'Closed trades',
    },
    {
      label: 'PnL (unrealized)',
      value: fmtCurrency(status?.pnl_unrealized),
      delta: fmtPercent(status?.pnl_unrealized_pct),
      note: 'Open exposure',
    },
    {
      label: 'Feed latency',
      value: fmtLatency(status?.market_latency_ms),
      note: `Spread ${latestSpread != null ? latestSpread.toFixed(2) : '--'} bp / Imbalance ${latestImbalance != null ? (latestImbalance * 100).toFixed(0) : '--'}%`,
    },
    {
      label: 'Risk / drawdown',
      value: fmtPercent(-(status?.max_drawdown_pct ?? 0)),
      note: `SL ${stopLossPct.toFixed(1)}% / TP ${takeProfitPct.toFixed(1)}% / Hit ${hitRateText}`,
    },
    {
      label: 'Position',
      value: (status?.position ?? 0).toFixed(4),
      note: `Bars in market: ${status?.position_age ?? 0}`,
    },
    holdBaseline
      ? {
          label: 'HODL baseline',
          value: fmtPercent(holdBaseline.pct),
          note: fmtCurrency(holdBaseline.pnl),
        }
      : null,
  ].filter(Boolean);

  return (
    <section className="metrics-grid" aria-label="Key metrics">
      {stats.map((item) => (
        <MetricCard key={item.label} {...item} />
      ))}
    </section>
  );
}
