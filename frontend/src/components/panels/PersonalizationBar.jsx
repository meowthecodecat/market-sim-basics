import React from "react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useData } from "../../context/DataContext.jsx";
import { useUI } from "../../context/UIContext.jsx";
import AudioController from "../widgets/AudioController.jsx";

export default function PersonalizationBar() {
  const { skin, skins, setSkin } = useTheme();
  const { state, dispatch } = useUI();
  const { status } = useData();

  return (
    <div className="personalization-bar">
      <div className="pill">PnL: {status ? `$${Number(status.pnl ?? 0).toFixed(2)}` : '--'}</div>
      <div className="pill-group" role="group" aria-label="Skins">
        {Object.entries(skins).map(([key, def]) => (
          <button
            key={key}
            className={`pill ${skin === key ? 'active' : ''}`}
            onClick={() => setSkin(key)}
            type="button"
          >
            {def.name}
          </button>
        ))}
      </div>
      <div className="pill-group">
        <button className={`pill ${state.focusMode ? 'active' : ''}`} onClick={() => dispatch({ type: 'TOGGLE_FOCUS' })} type="button">
          Focus mode
        </button>
        <button className={`pill ${state.largeText ? 'active' : ''}`} onClick={() => dispatch({ type: 'TOGGLE_LARGE_TEXT' })} type="button">
          Large type
        </button>
        <button className={`pill ${state.textOnly ? 'active' : ''}`} onClick={() => dispatch({ type: 'TOGGLE_TEXT_ONLY' })} type="button">
          Text only
        </button>
        <button className="pill" type="button" onClick={() => dispatch({ type: 'SHOW_SHORTCUTS' })}>
          Shortcuts
        </button>
        <AudioController />
      </div>
    </div>
  );
}
