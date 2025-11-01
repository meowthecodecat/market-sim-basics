import React, { useMemo } from 'react';
import { useTheme } from '../../context/ThemeContext.jsx';
import { useData } from '../../context/DataContext.jsx';
import { useUI } from '../../context/UIContext.jsx';
import { fmtDateTime } from '../../utils/format.js';

export default function HeaderSection() {
  const { theme, toggleTheme } = useTheme();
  const { status, orderbookDepth, setOrderbookDepth, error } = useData();
  const { dispatch } = useUI();

  const statusText = useMemo(() => {
    if (!status?.feed_status) return '';
    if (String(status.feed_status).startsWith('streaming')) return '';
    return `Live feed indisponible (${status.feed_status}). Utilisation du widget Kraken en fallback.`;
  }, [status]);

  return (
    <header className="hero">
      {statusText && <div className="status-banner" role="alert">{statusText}</div>}
      {error && <div className="status-banner warning">{error}</div>}
      <div className="hero__top">
        <div className="hero__title">
          <h1>BTC Live Bot</h1>
          <p>Track your bot in real time, feel the market mood, and spot signals the moment they appear.</p>
          <p className="hero__subtitle">Derniere mise a jour : {fmtDateTime(status?.last_update)}</p>
        </div>
        <div className="hero__actions">
          <div className="depth-control">
            <label htmlFor="depthRange">Depth {orderbookDepth}</label>
            <input
              id="depthRange"
              type="range"
              min="5"
              max="50"
              step="5"
              value={orderbookDepth}
              onChange={(event) => setOrderbookDepth(Number(event.target.value))}
            />
          </div>
          <button className="orderbook-toggle" onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}>
            Afficher l'order book
          </button>
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
          </button>
        </div>
      </div>
    </header>
  );
}
