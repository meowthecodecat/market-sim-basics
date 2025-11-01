import React from "react";
import { motion } from "framer-motion";

export default function MetricCard({ label, value, delta, note }) {
  return (
    <motion.article
      className="metric-card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
    >
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        {delta && <span className={`metric-delta ${String(delta).startsWith('-') ? 'neg' : 'pos'}`}>{delta}</span>}
      </div>
      <div className="metric-value">{value ?? '--'}</div>
      <div className="metric-note">{note ?? ''}</div>
    </motion.article>
  );
}
