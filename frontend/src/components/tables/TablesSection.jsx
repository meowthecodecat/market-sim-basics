import React from "react";
import CandlesTable from "./CandlesTable.jsx";
import TradesTable from "./TradesTable.jsx";
import HeatmapPositions from "../charts/HeatmapPositions.jsx";

export default function TablesSection() {
  return (
    <section className="tables-grid" aria-label="Data tables">
      <article className="panel">
        <div className="panel__header">
          <h2>Latest candles and patterns</h2>
        </div>
        <CandlesTable />
      </article>
      <article className="panel">
        <div className="panel__header">
          <h2>Executed trades</h2>
        </div>
        <TradesTable />
      </article>
      <HeatmapPositions />
    </section>
  );
}
