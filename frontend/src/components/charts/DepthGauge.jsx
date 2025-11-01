import React from 'react';

export default function DepthGauge({ value = 0 }) {
  const clamped = Math.max(-1, Math.min(1, Number(value)));
  const angle = (clamped + 1) * 90;
  const color = clamped > 0 ? '#4ade80' : clamped < 0 ? '#f87171' : '#94a3b8';

  const dashLead = Math.max(1, (clamped + 1) * 142);
  const dashTrail = Math.max(1, (1 - clamped) * 142);

  return (
    <div className="depth-gauge" role="img" aria-label={`Depth imbalance ${Math.round(clamped * 100)}%`}>
      <svg viewBox="0 0 200 120">
        <path d="M10 110 A90 90 0 0 1 190 110" fill="none" stroke="rgba(148,163,184,0.25)" strokeWidth="20" />
        <path
          d="M10 110 A90 90 0 0 1 190 110"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={`${dashLead} ${dashTrail}`}
          strokeLinecap="round"
        />
        <line
          x1="100"
          y1="110"
          x2={100 + 80 * Math.cos((angle - 180) * (Math.PI / 180))}
          y2={110 + 80 * Math.sin((angle - 180) * (Math.PI / 180))}
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
        />
      </svg>
      <div className="gauge-value">{(clamped * 100).toFixed(0)}%</div>
      <div className="gauge-note">{clamped > 0 ? 'Bid heavy' : clamped < 0 ? 'Ask heavy' : 'Balanced'}</div>
    </div>
  );
}
