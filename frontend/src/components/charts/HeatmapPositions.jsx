import React, { useMemo } from 'react';
import { useData } from '../../context/DataContext.jsx';

export default function HeatmapPositions() {
  const { trades } = useData();
  const grid = useMemo(() => {
    if (!trades?.length) return [];
    const grouped = {};
    trades.forEach((trade) => {
      const day = trade.t0?.slice(0, 10) ?? 'unknown';
      if (!grouped[day]) grouped[day] = [];
      grouped[day].push(Number(trade.pnl ?? 0));
    });
    return Object.entries(grouped)
      .map(([day, values]) => ({
        day,
        values,
        score: values.reduce((sum, val) => sum + val, 0),
      }))
      .sort((a, b) => (a.day > b.day ? -1 : 1))
      .slice(0, 10);
  }, [trades]);

  if (!grid.length) {
    return (
      <article className="panel">
        <div className="panel__header">
          <h2>Heatmap positions</h2>
        </div>
        <div className="heatmap-empty">Collecte en cours.</div>
      </article>
    );
  }

  const max = Math.max(...grid.map((item) => item.score));
  const min = Math.min(...grid.map((item) => item.score));
  const range = max - min || 1;

  return (
    <article className="panel heatmap-panel">
      <div className="panel__header">
        <h2>Heatmap positions</h2>
        <span className="panel__sub">PnL cumule par jour</span>
      </div>
      <div className="heatmap-grid">
        {grid.map((row) => {
          const intensity = (row.score - min) / range;
          return (
            <div key={row.day} className="heatmap-cell" style={{ background: `rgba(93, 139, 255, ${0.15 + intensity * 0.6})` }}>
              <span>{row.day}</span>
              <strong>{row.score >= 0 ? '+' : ''}{row.score.toFixed(2)}</strong>
            </div>
          );
        })}
      </div>
    </article>
  );
}
