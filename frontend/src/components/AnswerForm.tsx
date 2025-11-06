import React, { useState } from 'react';

interface Props {
  onSubmit: (answer: string) => void;
  disabled?: boolean;
}

export const AnswerForm: React.FC<Props> = ({ onSubmit, disabled }) => {
  const [value, setValue] = useState('');
  return (
    <form onSubmit={e => { e.preventDefault(); if (!value.trim()) return; onSubmit(value.trim()); setValue(''); }}>
      <input
        type="text"
        placeholder="Your answer"
        value={value}
        onChange={e => setValue(e.target.value)}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || value.trim().length === 0}>Submit Answer</button>
    </form>
  );
};
