import React, { useEffect, useRef } from 'react';
import { useTheme } from '../../context/ThemeContext.jsx';

const SCRIPT_ID = 'kraken-widget-embed';

export default function KrakenWidget() {
  const containerRef = useRef(null);
  const { theme } = useTheme();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = '';
    const div = document.createElement('div');
    div.className = 'kraken-widget';
    div.dataset.widget = 'price-ticker';
    div.dataset.theme = theme === 'light' ? 'light' : 'dark';
    div.dataset.base = 'USD';
    div.dataset.assets = 'BTC';
    div.dataset.interval = '1m';
    container.appendChild(div);

    const ensureScript = () => {
      if (document.getElementById(SCRIPT_ID)) {
        if (window.KrakenEmbed) {
          window.KrakenEmbed('refresh');
        }
        return;
      }
      const script = document.createElement('script');
      script.id = SCRIPT_ID;
      script.src = 'https://widgets.kraken.com/embed.js';
      script.async = true;
      script.onload = () => window.KrakenEmbed && window.KrakenEmbed('refresh');
      document.body.appendChild(script);
    };
    ensureScript();
  }, [theme]);

  return (
    <article className="panel kraken-widget-panel">
      <div className="panel__header">
        <h2>Fallback Kraken widget</h2>
        <span className="panel__sub">Donnees officielles embed</span>
      </div>
      <div className="kraken-widget-container" ref={containerRef}>
        <div className="kraken-widget-placeholder">Chargement du widget.</div>
      </div>
    </article>
  );
}
