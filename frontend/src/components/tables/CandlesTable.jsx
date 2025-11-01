import React from "react";
import { useData } from "../../context/DataContext.jsx";
import { fmtDateTime, fmtCurrency } from "../../utils/format.js";

export default function CandlesTable() {
  const { candles } = useData();
  const rows = (candles ?? []).slice(-30).reverse();
  return (
    <div className="table-wrapper">
      <table className="data-table" aria-label="Candles">
        <thead>
          <tr>
            <th>Date</th>
            <th>Close</th>
            <th>Signal</th>
            <th>Pattern</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.t0}>
              <td>{fmtDateTime(row.t0)}</td>
              <td>{fmtCurrency(row.close)}</td>
              <td className={row.signal_combined > 0 ? 'long' : row.signal_combined < 0 ? 'short' : 'flat'}>
                {row.signal_combined > 0 ? 'Long' : row.signal_combined < 0 ? 'Short' : 'Flat'}
              </td>
              <td>{row.engulfing === 1 ? 'Bullish engulfing' : row.engulfing === -1 ? 'Bearish engulfing' : row.hammer ? 'Hammer' : row.shooting_star ? 'Shooting star' : row.inside_bar ? 'Inside bar' : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
