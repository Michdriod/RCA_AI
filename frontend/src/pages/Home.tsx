import React from 'react';
import { ProblemInput } from '../components/ProblemInput';
import { QuestionCard } from '../components/QuestionCard';
import { AnswerForm } from '../components/AnswerForm';
import { ProgressIndicator } from '../components/ProgressIndicator';
import { RootCauseView } from '../components/RootCauseView';
import { useSession } from '../hooks/useSession';

const Home: React.FC = () => {
  const {
    sessionId,
    problem,
    setProblem,
    currentQuestion,
    step,
    status,
    rootCause,
    start,
    answer,
    next,
    finalizeSession,
    loading,
    error,
    canAnswer,
    canNext,
    reset
  } = useSession();

  return (
    <div className="app-container">
      <h1>5 Whys Root Cause Analysis</h1>
      {!sessionId && status === 'idle' && (
        <ProblemInput
          problem={problem}
            onChange={setProblem}
            onSubmit={() => start(problem)}
          loading={loading}
        />
      )}
      {error && <div className="error">{error}</div>}
      {sessionId && status !== 'complete' && (
        <>
          <ProgressIndicator step={step} total={5} />
          {currentQuestion && <QuestionCard question={currentQuestion} />}
          {canAnswer && <AnswerForm onSubmit={answer} disabled={loading} />}
          <div className="actions">
            <button onClick={next} disabled={!canNext || loading}>Next</button>
            <button onClick={finalizeSession} disabled={loading}>Finalize</button>
          </div>
        </>
      )}
      {status === 'complete' && rootCause && (
        <RootCauseView rootCause={rootCause} onRestart={reset} />
      )}
      <footer className="footer">Session Status: {status.toUpperCase()}</footer>
    </div>
  );
};

export default Home;
