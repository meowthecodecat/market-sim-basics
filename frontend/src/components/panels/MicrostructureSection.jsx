import React from "react";
import MicrostructurePanel from "./MicrostructurePanel.jsx";
import KrakenWidget from "../widgets/KrakenWidget.jsx";
import PerformanceBadges from "../widgets/PerformanceBadges.jsx";

export default function MicrostructureSection() {
  return (
    <section className="microstructure-grid" aria-label="Market microstructure">
      <MicrostructurePanel />
      <PerformanceBadges />
      <KrakenWidget />
    </section>
  );
}
