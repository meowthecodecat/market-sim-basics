const REFRESH_INTERVAL = 5000;

const fmtCurrency = (value) =>
  typeof value === "number" && Number.isFinite(value) ? `$${value.toFixed(2)}` : "--";

const fmtPercent = (value) =>
  typeof value === "number" && Number.isFinite(value)
    ? `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
    : "--";

const fmtDate = (iso) => {
  if (!iso) return "--";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "--";
  return d.toLocaleString("fr-FR", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    day: "2-digit",
    month: "short",
  });
};

async function fetchJson(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error(`Error loading ${url}`, error);
    return null;
  }
}

function useDashboardData() {
  const [data, setData] = React.useState({
    status: null,
    candles: [],
    equity: [],
    trades: [],
  });

  React.useEffect(() => {
    let mounted = true;

    const load = async () => {
      const [status, candles, equity, trades] = await Promise.all([
        fetchJson("/status"),
        fetchJson("/candles?limit=200"),
        fetchJson("/equity?limit=400"),
        fetchJson("/bot_trades?limit=120"),
      ]);
      if (!mounted) return;
      setData({
        status,
        candles: candles?.candles ?? [],
        equity: equity?.equity ?? [],
        trades: trades?.trades ?? [],
      });
    };

    load();
    const id = setInterval(load, REFRESH_INTERVAL);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return data;
}

function patternLabel(row) {
  if (!row) return "";
  if (row.hammer) return "Hammer";
  if (row.shooting_star) return "Shooting Star";
  if (row.engulfing === 1) return "Bullish Engulfing";
  if (row.engulfing === -1) return "Bearish Engulfing";
  if (row.inside_bar) return "Inside Bar";
  return "";
}

function signalClass(signal) {
  if (signal > 0) return "signal-chip long";
  if (signal < 0) return "signal-chip short";
  return "signal-chip flat";
}

function useCandleChart(containerRef, candles) {
  const chartRef = React.useRef(null);

  React.useEffect(() => {
    if (!window.LightweightCharts || !containerRef.current) return;
    if (chartRef.current) return;

    const chart = LightweightCharts.createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      layout: {
        background: { type: "solid", color: "transparent" },
        textColor: "rgba(226, 232, 240, 0.8)",
        fontFamily: "Space Grotesk",
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.12)" },
        horzLines: { color: "rgba(148, 163, 184, 0.12)" },
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
      },
    });

    const series = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const handleResize = () => {
      if (!containerRef.current) return;
      chart.applyOptions({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      });
    };

    window.addEventListener("resize", handleResize);
    chartRef.current = { chart, series, handleResize };

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [containerRef]);

  React.useEffect(() => {
    if (!chartRef.current || !candles.length) return;
    const mapped = candles.map((candle) => ({
      time: Math.floor(new Date(candle.t0).getTime() / 1000),
      open: Number(candle.open),
      high: Number(candle.high),
      low: Number(candle.low),
      close: Number(candle.close),
    }));
    chartRef.current.series.setData(mapped);
    chartRef.current.chart.timeScale().fitContent();
  }, [candles]);
}

function useEquityChart(canvasRef, equity) {
  const chartRef = React.useRef(null);

  React.useEffect(() => {
    if (!window.Chart || !canvasRef.current) return;
    if (chartRef.current) return;

    const ctx = canvasRef.current.getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, canvasRef.current.height);
    gradient.addColorStop(0, "rgba(56, 189, 248, 0.35)");
    gradient.addColorStop(1, "rgba(15, 23, 42, 0)");

    const chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Equity",
            data: [],
            borderColor: "#38bdf8",
            borderWidth: 2.4,
            backgroundColor: gradient,
            pointRadius: 0,
            fill: true,
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.92)",
            borderColor: "rgba(56, 189, 248, 0.45)",
            borderWidth: 1,
            callbacks: {
              label: (ctx) => fmtCurrency(ctx.raw),
            },
          },
        },
        scales: {
          x: {
            ticks: { color: "rgba(226, 232, 240, 0.6)" },
            grid: { display: false },
          },
          y: {
            ticks: {
              color: "rgba(226, 232, 240, 0.6)",
              callback: (val) => `$${val}`,
            },
            grid: { color: "rgba(148, 163, 184, 0.1)" },
          },
        },
      },
    });

    chartRef.current = chart;
    return () => {
      chart.destroy();
      chartRef.current = null;
    };
  }, [canvasRef]);

  React.useEffect(() => {
    if (!chartRef.current) return;
    const labels = equity.map((row) => fmtDate(row.t0));
    const values = equity.map((row) => Number(row.equity));
    chartRef.current.data.labels = labels;
    chartRef.current.data.datasets[0].data = values;
    chartRef.current.update("none");
  }, [equity]);
}

function Metrics({ status }) {
  const priceChange = status?.price_change_pct;
  const priceBadgeClass = priceChange > 0 ? "badge badge--pos" : priceChange < 0 ? "badge badge--neg" : "badge";
  const pnlBadgeClass = status?.pnl_pct > 0 ? "badge badge--pos" : status?.pnl_pct < 0 ? "badge badge--neg" : "badge";
  const realizedBadgeClass = status?.pnl_realized > 0 ? "badge badge--pos" : status?.pnl_realized < 0 ? "badge badge--neg" : "badge";
  const unrealizedBadgeClass = status?.pnl_unrealized > 0 ? "badge badge--pos" : status?.pnl_unrealized < 0 ? "badge badge--neg" : "badge";
  const priceUpdated = fmtDate(status?.price_timestamp);
  const priceReference = fmtDate(status?.price_reference_ts);

  return (
    <section className="metrics-grid">
      <article className="metric-card">
        <div className="metric-top">
          <span className="metric-label">Initial capital</span>
        </div>
        <div className="metric-value">{fmtCurrency(status?.initial_cash)}</div>
        <div className="metric-note">Base stake</div>
      </article>
      <article className="metric-card">
        <div className="metric-top">
          <span className="metric-label">Equity</span>
        </div>
        <div className="metric-value">{fmtCurrency(status?.equity)}</div>
        <div className="metric-note">Trades executed: {status?.n_trades ?? 0}</div>
      </article>
      <article className="metric-card">
        <div className="metric-top">
          <span className="metric-label">BTC/USD</span>
        </div>
        <div className="metric-value">{fmtCurrency(status?.last_price)}</div>
        <div className="metric-foot metric-foot--split">
          <span className={priceBadgeClass}>{fmtPercent(priceChange)}</span>
          <span className="metric-note">Updated {priceUpdated}<br />Ref {priceReference}</span>
        </div>
      </article>
      <article className="metric-card">
        <div className="metric-top">
          <span className="metric-label">PnL (total)</span>
        </div>
        <div className="metric-value">{fmtCurrency(status?.pnl)}</div>
        <div className="metric-foot">
          <span className={pnlBadgeClass}>{fmtPercent(status?.pnl_pct)}</span>
          <span className="metric-note">vs initial</span>
        </div>
      </article>
      <article className="metric-card">
        <div className="metric-top">
          <span className="metric-label">PnL (realized)</span>
        </div>
        <div className="metric-value">{fmtCurrency(status?.pnl_realized)}</div>
        <div className="metric-foot">
          <span className={realizedBadgeClass}>{fmtPercent(status?.pnl_realized_pct)}</span>
          <span className="metric-note">Closed trades</span>
        </div>
      </article>
      <article className="metric-card">
        <div className="metric-top">
          <span className="metric-label">PnL (unrealized)</span>
        </div>
        <div className="metric-value">{fmtCurrency(status?.pnl_unrealized)}</div>
        <div className="metric-foot">
          <span className={unrealizedBadgeClass}>{fmtPercent(status?.pnl_unrealized_pct)}</span>
          <span className="metric-note">Open exposure</span>
        </div>
      </article>
    </section>
  );
}

function CandlesTable({ candles }) {
  const rows = React.useMemo(() => (candles ?? []).slice(-30).reverse(), [candles]);
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Price</th>
            <th>Signal</th>
            <th>Pattern</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${row.t0}-${idx}`}>
              <td>{fmtDate(row.t0)}</td>
              <td>{fmtCurrency(Number(row.close))}</td>
              <td>
                <span className={signalClass(row.signal_candle)}>
                  {row.signal_candle > 0 ? "Long" : row.signal_candle < 0 ? "Short" : "Flat"}
                </span>
              </td>
              <td>{patternLabel(row) || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TradesTable({ trades }) {
  const rows = React.useMemo(() => (trades ?? []).slice(-60).reverse(), [trades]);
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Action</th>
            <th>Price</th>
            <th>Equity</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${row.t0}-${idx}`}>
              <td>{fmtDate(row.t0)}</td>
              <td>{row.action ?? "-"}</td>
              <td>{fmtCurrency(Number(row.price))}</td>
              <td>{fmtCurrency(Number(row.equity))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Dashboard() {
  const { status, candles, equity, trades } = useDashboardData();
  const candleContainerRef = React.useRef(null);
  const equityCanvasRef = React.useRef(null);

  useCandleChart(candleContainerRef, candles);
  useEquityChart(equityCanvasRef, equity);

  return (
    <div className="dashboard">
      <header className="hero">
        <div className="hero__title">
          <h1>BTC Live Bot</h1>
          <p>Track your bot in real time and watch the signals unfold.</p>
        </div>
        <Metrics status={status} />
      </header>

      <section className="charts-grid">
        <article className="panel">
          <div className="panel__header">
            <h2>BTC/USD - Candlesticks</h2>
            <span className="panel__sub">Updated every 5 seconds</span>
          </div>
          <div className="candle-chart-container" ref={candleContainerRef}></div>
        </article>
        <article className="panel">
          <div className="panel__header">
            <h2>Bot equity</h2>
            <span className="panel__sub">Recent capital evolution</span>
          </div>
          <div className="equity-chart-container">
            <canvas ref={equityCanvasRef}></canvas>
          </div>
        </article>
      </section>

      <section className="tables-grid">
        <article className="panel">
          <div className="panel__header">
            <h2>Latest candles and patterns</h2>
          </div>
          <CandlesTable candles={candles} />
        </article>
        <article className="panel">
          <div className="panel__header">
            <h2>Executed trades</h2>
          </div>
          <TradesTable trades={trades} />
        </article>
      </section>

      <footer className="footer">
        Powered by Kraken live data. Real-time simulation. Built for inspired traders.
      </footer>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<Dashboard />);


