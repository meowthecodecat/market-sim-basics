import React from "react";
import { useData } from "../../context/DataContext.jsx";
import { fmtCurrency, fmtDateTime } from "../../utils/format.js";

export default function TradesTable() {
  const { trades } = useData();
  const rows = (trades ?? []).slice(-60).reverse();
  return (
    <div className="table-wrapper trade-tables">
      <table className="data-table" aria-label="Trades">
        <thead>
          <tr>
            <th>Date</th>
            <th>Action</th>
            <th>Price</th>
            <th>Equity</th>
            <th>PnL</th>
            <th>Context</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${row.t0}-${idx}`}>
              <td>{fmtDateTime(row.t0)}</td>
              <td>{row.action ?? '-'}</td>
              <td>{fmtCurrency(row.price)}</td>
              <td>{fmtCurrency(row.equity)}</td>
              <td className={Number(row.pnl ?? 0) >= 0 ? 'long' : 'short'}>{fmtCurrency(row.pnl ?? 0)}</td>
              <td>{row.context ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
