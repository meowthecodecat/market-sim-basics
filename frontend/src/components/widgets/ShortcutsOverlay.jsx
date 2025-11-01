import React from "react";
import { useUI } from "../../context/UIContext.jsx";

const shortcuts = [
  { keys: 'O', label: "Toggle order book" },
  { keys: 'T', label: "Toggle theme" },
  { keys: 'F', label: "Focus mode" },
  { keys: 'L', label: "Large typography" },
  { keys: 'S', label: "Toggle sound" },
  { keys: '?', label: "Close overlay" },
];

export default function ShortcutsOverlay() {
  const { dispatch } = useUI();
  return (
    <div className="shortcuts-overlay" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" onClick={() => dispatch({ type: 'HIDE_SHORTCUTS' })}>
      <div className="shortcuts-panel" onClick={(e) => e.stopPropagation()}>
        <h2>Raccourcis clavier</h2>
        <ul>
          {shortcuts.map((item) => (
            <li key={item.keys}>
              <kbd>{item.keys}</kbd>
              <span>{item.label}</span>
            </li>
          ))}
        </ul>
        <button className="primary" onClick={() => dispatch({ type: 'HIDE_SHORTCUTS' })}>Fermer</button>
      </div>
    </div>
  );
}
