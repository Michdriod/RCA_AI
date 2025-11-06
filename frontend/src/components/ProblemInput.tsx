import React from 'react';

interface Props {
  problem: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading?: boolean;
}

export const ProblemInput: React.FC<Props> = ({ problem, onChange, onSubmit, loading }) => {
  return (
    <form onSubmit={e => { e.preventDefault(); onSubmit(); }}>
      <label style={{ fontWeight: 600 }}>Describe the problem</label>
      <textarea
        rows={3}
        value={problem}
        onChange={e => onChange(e.target.value)}
        placeholder="e.g. API latency spike every morning"
        disabled={loading}
      />
      <button type="submit" disabled={loading || problem.trim().length < 3}>Start Analysis</button>
    </form>
  );
};
