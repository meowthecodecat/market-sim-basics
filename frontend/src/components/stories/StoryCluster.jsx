import React, { useMemo } from 'react';
import { useData } from '../../context/DataContext.jsx';
import Leaderboard from '../panels/Leaderboard.jsx';
import { fmtCurrency } from '../../utils/format.js';

function buildNarrative(status, marketMetrics, bestTrade, worstTrade) {
  if (!status) return 'En attente des premieres donnees...';
  const latency = Number(status.market_latency_ms ?? 0);
  const spread = marketMetrics?.latest?.spread_bp ?? null;
  const imbalance = marketMetrics?.latest?.depth_imbalance ?? null;
  const pnl = Number(status.pnl ?? 0);

  const lines = [];
  if (Math.abs(pnl) < 1) {
    lines.push("PnL neutre pour l'instant. Le bot observe et attend une impulsion nette.");
  } else if (pnl > 0) {
    lines.push(`PnL positif ${fmtCurrency(pnl)} : humeur confiante.`);
  } else {
    lines.push(`PnL negatif ${fmtCurrency(pnl)}. Vigilance recommandee.`);
  }

  if (spread != null) {
    const tone = spread < 1 ? 'tres serres' : spread < 3 ? 'moderes' : 'larges';
    lines.push(`Spreads ${tone} (${spread.toFixed(2)} bp).`);
  }

  if (imbalance != null) {
    if (Math.abs(imbalance) < 0.1) {
      lines.push('Carnet equilibre, aucune domination nette.');
    } else {
      lines.push(`Carnet ${imbalance > 0 ? 'acheteurs' : 'vendeurs'} (imbalance ${(imbalance * 100).toFixed(0)}%).`);
    }
  }

  if (latency > 5000) {
    lines.push('Latence elevee detectee : fallback Kraken actif.');
  }

  if (bestTrade) {
    lines.push(`Meilleur trade: ${bestTrade.action ?? '-'} a ${fmtCurrency(bestTrade.price)} (${fmtCurrency(bestTrade.pnl)}).`);
  }
  if (worstTrade) {
    lines.push(`Worst trade: ${worstTrade.action ?? '-'} a ${fmtCurrency(worstTrade.price)} (${fmtCurrency(worstTrade.pnl)}).`);
  }

  return lines.join(' ');
}

export default function StoryCluster() {
  const { status, marketMetrics, bestTrade, worstTrade, badges } = useData();
  const text = useMemo(
    () => buildNarrative(status, marketMetrics, bestTrade, worstTrade),
    [status, marketMetrics, bestTrade, worstTrade],
  );

  const badgeList = badges?.length ? badges : [{ label: 'Patience', detail: 'En attente de signaux' }];

  return (
    <section className="story-cluster">
      <article className="story-card">
        <h2>Market mood</h2>
        <p>{text}</p>
      </article>
      <article className="story-card">
        <h2>Badges & highlights</h2>
        <ul>
          {badgeList.map((badge) => (
            <li key={badge.label}>
              <span className="badge-title">{badge.label}</span>
              <span className="badge-detail">{badge.detail}</span>
            </li>
          ))}
        </ul>
      </article>
      <Leaderboard />
    </section>
  );
}
