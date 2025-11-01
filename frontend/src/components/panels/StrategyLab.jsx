import React, { useState } from 'react';
import { useData } from '../../context/DataContext.jsx';

export default function StrategyLab() {
  const { status } = useData();
  const [form, setForm] = useState({
    stop_loss_pct: status?.stop_loss_pct ?? 0.01,
    take_profit_pct: status?.take_profit_pct ?? 0.02,
    trailing_stop_pct: status?.trailing_stop_pct ?? 0.01,
    position_scale: status?.position_scale ?? 1.0,
  });
  const [message, setMessage] = useState(null);

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const submit = async () => {
    try {
      const response = await fetch('/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      setMessage('Configuration mise a jour');
      setTimeout(() => setMessage(null), 2500);
    } catch (err) {
      setMessage("Erreur lors de l'envoi");
      setTimeout(() => setMessage(null), 2500);
    }
  };

  return (
    <section className="panel strategy-lab" aria-label="Strategy lab">
      <div className="panel__header">
        <h2>Strategy lab</h2>
        <span className="panel__sub">Ajuste les parametres en direct</span>
      </div>
      <div className="lab-grid">
        <label>
          Stop loss
          <input
            type="range"
            min="0"
            max="0.05"
            step="0.0025"
            value={form.stop_loss_pct}
            onChange={(e) => handleChange('stop_loss_pct', Number(e.target.value))}
          />
          <span>{(form.stop_loss_pct * 100).toFixed(2)}%</span>
        </label>
        <label>
          Take profit
          <input
            type="range"
            min="0"
            max="0.08"
            step="0.005"
            value={form.take_profit_pct}
            onChange={(e) => handleChange('take_profit_pct', Number(e.target.value))}
          />
          <span>{(form.take_profit_pct * 100).toFixed(2)}%</span>
        </label>
        <label>
          Trailing stop
          <input
            type="range"
            min="0"
            max="0.05"
            step="0.005"
            value={form.trailing_stop_pct}
            onChange={(e) => handleChange('trailing_stop_pct', Number(e.target.value))}
          />
          <span>{(form.trailing_stop_pct * 100).toFixed(2)}%</span>
        </label>
        <label>
          Position scale
          <input
            type="range"
            min="0.2"
            max="2"
            step="0.1"
            value={form.position_scale}
            onChange={(e) => handleChange('position_scale', Number(e.target.value))}
          />
          <span>{form.position_scale.toFixed(2)}x</span>
        </label>
      </div>
      <button className="primary" onClick={submit} type="button">
        Mettre a jour
      </button>
      {message && <p className="lab-message">{message}</p>}
    </section>
  );
}
