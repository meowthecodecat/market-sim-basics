import React, { useMemo } from 'react';
import { useData } from '../../context/DataContext.jsx';
import { fmtCurrency, fmtPercent } from '../../utils/format.js';

export default function KrakenWidget() {
  const { marketMetrics } = useData();
  const latest = marketMetrics?.latest ?? {};
  const history = marketMetrics?.history ?? [];

  const summary = useMemo(() => {
    const toNumber = (value) => (typeof value === 'number' ? value : Number.isFinite(Number(value)) ? Number(value) : null);
    const mid = toNumber(latest.mid);
    const spread = toNumber(latest.spread);
    const spreadBp = toNumber(latest.spread_bp);
    const depthImbalance = toNumber(latest.depth_imbalance);
    const bidVolume = toNumber(latest.bid_volume);
    const askVolume = toNumber(latest.ask_volume);

    const prevEntry = [...history].reverse().find((entry) => {
      const candidate = toNumber(entry?.mid);
      return candidate != null && candidate !== 0;
    });
    const prevMid = prevEntry ? toNumber(prevEntry.mid) : null;

    let changePct = null;
    if (mid != null && prevMid != null && prevMid !== 0) {
      changePct = ((mid - prevMid) / prevMid) * 100;
    }

    return {
      mid,
      spread,
      spreadBp,
      depthImbalance,
      bidVolume,
      askVolume,
      changePct,
    };
  }, [history, latest]);

  const {
    mid, spread, spreadBp, depthImbalance, bidVolume, askVolume, changePct,
  } = summary;

  const imbalanceClass = depthImbalance > 0 ? 'imb-pos' : depthImbalance < 0 ? 'imb-neg' : 'imb-neutral';
  const changeClass = changePct > 0 ? 'imb-pos' : changePct < 0 ? 'imb-neg' : 'imb-neutral';

  return (
    <article className="panel kraken-widget-panel">
      <div className="panel__header">
        <h2>Spot BTC/USD</h2>
        <span className="panel__sub">Donnees internes Kraken</span>
      </div>
      <div className="kraken-widget-container">
        <div className="kraken-widget-price">
          <span className="micro-label">Mid price</span>
          <strong>{mid != null ? fmtCurrency(mid, { minimumFractionDigits: 2 }) : '--'}</strong>
          <span className={`micro-diff ${changeClass}`}>
            {changePct != null ? fmtPercent(changePct, { decimals: 2 }) : '--'}
          </span>
        </div>
        <div className="kraken-widget-grid">
          <div>
            <span className="micro-label">Spread</span>
            <strong>{spread != null ? fmtCurrency(spread, { minimumFractionDigits: 2, maximumFractionDigits: 4 }) : '--'}</strong>
          </div>
          <div>
            <span className="micro-label">Spread (bp)</span>
            <strong>{spreadBp != null ? spreadBp.toFixed(2) : '--'} bp</strong>
          </div>
          <div>
            <span className="micro-label">Depth imbalance</span>
            <strong className={imbalanceClass}>
              {depthImbalance != null ? fmtPercent(depthImbalance * 100, { decimals: 1 }) : '--'}
            </strong>
          </div>
          <div>
            <span className="micro-label">Bid vol</span>
            <strong>{bidVolume != null ? bidVolume.toFixed(2) : '--'}</strong>
          </div>
          <div>
            <span className="micro-label">Ask vol</span>
            <strong>{askVolume != null ? askVolume.toFixed(2) : '--'}</strong>
          </div>
        </div>
        <p className="kraken-widget-note">
          Impossible de charger le script officiel Kraken, affichage des metriques internes a la place.
        </p>
      </div>
    </article>
  );
}
