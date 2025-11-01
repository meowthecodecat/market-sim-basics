import React, { useMemo } from "react";

export default function LatencySparkline({ data }) {
  const points = useMemo(() => {
    if (!data?.length) return null;
    const sanitized = data.slice(-50);
    const values = sanitized.map((item) => Number(item.value ?? 0));
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = max - min || 1;
    return sanitized
      .map((entry, index) => {
        const x = (index / (sanitized.length - 1 || 1)) * 100;
        const y = 100 - ((Number(entry.value ?? 0) - min) / range) * 100;
        return `${x},${y}`;
      })
      .join(' ');
  }, [data]);

  return (
    <div className="latency-card">
      <div className="latency-header">Latency history</div>
      {points ? (
        <svg viewBox="0 0 100 100" className="latency-sparkline">
          <polyline fill="none" stroke="var(--accent)" strokeWidth="2" points={points} />
        </svg>
      ) : (
        <div className="latency-empty">--</div>
      )}
    </div>
  );
}
