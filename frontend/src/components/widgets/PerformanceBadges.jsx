import React from 'react';
import { useData } from '../../context/DataContext.jsx';

const defaultBadges = [
  { label: 'Warm-up', detail: 'Collect more data to unlock badges.' },
];

export default function PerformanceBadges() {
  const { badges } = useData();
  const list = badges?.length ? badges : defaultBadges;

  return (
    <article className="panel badges-panel">
      <div className="panel__header">
        <h2>Performance badges</h2>
        <span className="panel__sub">Gamification et milestones</span>
      </div>
      <ul className="badge-list">
        {list.map((badge) => (
          <li key={badge.label}>
            <span className="badge-icon" aria-hidden="true">?</span>
            <div>
              <strong>{badge.label}</strong>
              <p>{badge.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </article>
  );
}
