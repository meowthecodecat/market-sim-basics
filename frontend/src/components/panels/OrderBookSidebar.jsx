import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useData } from '../../context/DataContext.jsx';
import { useUI } from '../../context/UIContext.jsx';
import { fmtBookPrice, fmtBookQty, fmtLatency } from '../../utils/format.js';

export default function OrderBookSidebar({ open }) {
  const { orderbook } = useData();
  const { dispatch } = useUI();
  const bids = orderbook?.bids ?? [];
  const asks = orderbook?.asks ?? [];
  const latency = orderbook?.latency_ms ?? null;

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="orderbook-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR', value: false })}
          />
          <motion.aside
            className="orderbook-sidebar"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 210, damping: 26 }}
          >
            <div className="orderbook-sidebar__header">
              <div>
                <h2>Order Book</h2>
                <span className="orderbook-sidebar__depth">Depth {Math.max(bids.length, asks.length)}</span>
              </div>
              <button className="orderbook-close" onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR', value: false })}>
                X
              </button>
            </div>
            <div className="orderbook-sidebar__meta">
              <span>{orderbook?.timestamp ? new Date(orderbook.timestamp).toLocaleTimeString('fr-FR', { hour12: false }) : 'En attente du flux.'}</span>
              <span className={`latency-badge ${latency > 2000 ? 'latency-badge--warn' : ''}`}>Latency {fmtLatency(latency)}</span>
            </div>
            <div className="orderbook-sidebar__grid">
              <div className="orderbook-column orderbook-column--asks">
                <div className="orderbook-column__title">Asks</div>
                <table className="orderbook-table orderbook-table--asks">
                  <thead>
                    <tr>
                      <th>Qty</th>
                      <th>Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {asks.map((level, idx) => (
                      <tr key={`ask-${idx}`}>
                        <td>{fmtBookQty(level.qty)}</td>
                        <td>{fmtBookPrice(level.price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="orderbook-column orderbook-column--bids">
                <div className="orderbook-column__title">Bids</div>
                <table className="orderbook-table orderbook-table--bids">
                  <thead>
                    <tr>
                      <th>Qty</th>
                      <th>Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bids.map((level, idx) => (
                      <tr key={`bid-${idx}`}>
                        <td>{fmtBookQty(level.qty)}</td>
                        <td>{fmtBookPrice(level.price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
