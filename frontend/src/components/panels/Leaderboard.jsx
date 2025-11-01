import React from "react";
import { useData } from "../../context/DataContext.jsx";
import { fmtCurrency, fmtPercent } from "../../utils/format.js";

const competitors = [
  { id: 'hold', label: 'HODL baseline' },
  { id: 'flat', label: 'Flat (0%)' },
  { id: 'bot', label: 'Live bot' },
];

export default function Leaderboard() {
  const { status, holdBaseline } = useData();
  const entries = competitors.map((row) => {
    if (row.id === 'bot') {
      return { ...row, pnl: status?.pnl ?? 0, pct: status?.pnl_pct ?? 0 };
    }
    if (row.id === 'hold') {
      return { ...row, pnl: holdBaseline?.pnl ?? 0, pct: holdBaseline?.pct ?? 0 };
    }
    return { ...row, pnl: 0, pct: 0 };
  }).sort((a, b) => b.pnl - a.pnl);

  return (
    <article className="panel leaderboard">
      <div className="panel__header">
        <h2>Leaderboard</h2>
        <span className="panel__sub">Comparaison rapide</span>
      </div>
      <ul>
        {entries.map((entry) => (
          <li key={entry.id} className={entry.id === 'bot' ? 'highlight' : ''}>
            <span>{entry.label}</span>
            <span>{fmtCurrency(entry.pnl)} ({fmtPercent(entry.pct)})</span>
          </li>
        ))}
      </ul>
    </article>
  );
}
