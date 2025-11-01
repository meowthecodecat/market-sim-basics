import React from "react";
import { useTheme } from "../../context/ThemeContext.jsx";

export default function ThemeGallery() {
  const { skins, skin, setSkin } = useTheme();
  return (
    <section className="panel theme-gallery">
      <div className="panel__header">
        <h2>Skins gallery</h2>
        <span className="panel__sub">Change la vibe du dashboard</span>
      </div>
      <div className="skin-grid">
        {Object.entries(skins).map(([key, def]) => (
          <button
            key={key}
            className={`skin-card ${skin === key ? 'active' : ''}`}
            onClick={() => setSkin(key)}
          >
            <span className="skin-name">{def.name}</span>
            <span className="skin-desc">{def.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
