import React from 'react';
import { useData } from '../../context/DataContext.jsx';
import { fmtCurrency, fmtPercent } from '../../utils/format.js';

export default function MicrostructurePanel() {
  const { marketMetrics, timeline } = useData();
  const latest = marketMetrics?.latest ?? {};

  return (
    <article className="panel micro-panel">
      <div className="panel__header">
        <h2>Microstructure live</h2>
        <span className="panel__sub">Top-book et order flow</span>
      </div>
      <div className="micro-panel__stats">
        <div>
          <span className="micro-label">Spread</span>
          <strong>{latest.spread ? fmtCurrency(latest.spread, { minimumFractionDigits: 4 }) : '--'}</strong>
        </div>
        <div>
          <span className="micro-label">Spread (bp)</span>
          <strong>{latest.spread_bp != null ? latest.spread_bp.toFixed(2) : '--'} bp</strong>
        </div>
        <div>
          <span className="micro-label">Depth imbalance</span>
          <strong className={latest.depth_imbalance > 0 ? 'imb-pos' : latest.depth_imbalance < 0 ? 'imb-neg' : 'imb-neutral'}>
            {latest.depth_imbalance != null ? (latest.depth_imbalance * 100).toFixed(0) : '--'}%
          </strong>
        </div>
        <div>
          <span className="micro-label">Volatilite</span>
          <strong>{fmtPercent((marketMetrics?.volatility ?? 0) * 100)}</strong>
        </div>
      </div>
      <div className="micro-timeline">
        {timeline.slice(-40).map((item) => (
          <div key={item.time} className={`micro-tick ${item.signal > 0 ? 'long' : item.signal < 0 ? 'short' : 'flat'}`} />
        ))}
      </div>
    </article>
  );
}
