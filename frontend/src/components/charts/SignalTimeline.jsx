import React from 'react';
import clsx from 'clsx';

export default function SignalTimeline({ data }) {
  if (!data?.length) return <div className="timeline-empty">Pas encore de signaux</div>;
  const items = data.slice(-60);
  return (
    <div className="signal-timeline" aria-label="Signal timeline">
      {items.map((item) => (
        <div
          key={item.time}
          className={clsx('signal-dot', {
            long: item.signal > 0,
            short: item.signal < 0,
            flat: item.signal === 0,
          })}
          title={`${item.time} | signal ${item.signal}`}
        >
          <span />
        </div>
      ))}
    </div>
  );
}
