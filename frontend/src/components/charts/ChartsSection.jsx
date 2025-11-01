import React, { useEffect, useRef } from "react";
import { useData } from "../../context/DataContext.jsx";
import SignalTimeline from "./SignalTimeline.jsx";
import DepthGauge from "./DepthGauge.jsx";
import LatencySparkline from "./LatencySparkline.jsx";
import { fmtPercent } from "../../utils/format.js";

export default function ChartsSection() {
  const { equity, timeline, depthGauge, spreadBp, latencySeries } = useData();
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;
    import('chart.js').then(({ Chart }) => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
      const ctx = chartRef.current.getContext('2d');
      chartInstanceRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels: equity.map((row) => row.t0),
          datasets: [
            {
              label: 'Equity',
              data: equity.map((row) => Number(row.equity ?? 0)),
              borderColor: '#5d8bff',
              backgroundColor: 'rgba(93, 139, 255, 0.18)',
              pointRadius: 0,
              fill: true,
              tension: 0.35,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { display: false }, grid: { display: false } },
            y: { ticks: { color: 'rgba(226, 232, 240, 0.6)' }, grid: { color: 'rgba(148, 163, 184, 0.12)' } },
          },
        },
      });
    });
    return () => {
      if (chartInstanceRef.current) chartInstanceRef.current.destroy();
    };
  }, [equity]);

  return (
    <section className="charts-grid" aria-label="Charts">
      <article className="panel chart-panel">
        <div className="panel__header">
          <h2>Bot equity</h2>
          <span className="panel__sub">Recent capital evolution</span>
        </div>
        <div className="equity-chart-container">
          <canvas ref={chartRef} />
        </div>
        <SignalTimeline data={timeline} />
      </article>
      <article className="panel chart-panel mini">
        <div className="panel__header">
          <h2>Depth gauge</h2>
          <span className="panel__sub">Spread {spreadBp ? fmtPercent(spreadBp, { decimals: 2 }) : '--'}</span>
        </div>
        <DepthGauge value={depthGauge} />
        <LatencySparkline data={latencySeries} />
      </article>
    </section>
  );
}
