import React from 'react';

interface Props { step: number; total: number; }

export const ProgressIndicator: React.FC<Props> = ({ step, total }) => {
  return (
    <div className="progress" aria-label="Progress steps">
      {Array.from({ length: total }, (_, i) => i + 1).map(n => (
        <span key={n} className={n <= step ? 'active' : ''}>{n}</span>
      ))}
    </div>
  );
};
