import React from 'react';
import type { Question } from '../types/session';

export const QuestionCard: React.FC<{ question: Question }> = ({ question }) => {
  return (
    <div className="question-card">
      <strong>Question {question.index}:</strong>
      <div>{question.text}</div>
    </div>
  );
};
