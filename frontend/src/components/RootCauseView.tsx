import React from 'react';
import type { RootCause } from '../types/session';

interface Props {
  rootCause: RootCause;
  onRestart: () => void;
}

export const RootCauseView: React.FC<Props> = ({ rootCause, onRestart }) => {
  return (
    <div className="root-cause">
      <h2>Root Cause</h2>
      <p><strong>Summary:</strong> {rootCause.summary}</p>
      <h3>Contributing Factors</h3>
      <ul>
        {rootCause.contributing_factors.map(f => <li key={f}>{f}</li>)}
      </ul>
      <button onClick={onRestart}>Start New Session</button>
    </div>
  );
};
