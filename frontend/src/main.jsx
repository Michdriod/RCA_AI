import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles/global.css';
import { ProblemInput } from './components/ProblemInput';
import { QuestionCard } from './components/QuestionCard';
import { AnswerForm } from './components/AnswerForm';
import { ProgressIndicator } from './components/ProgressIndicator';
import { RootCauseView } from './components/RootCauseView';
import { useSessionFlow } from './services/useSessionFlow';

function App() {
  const {
    sessionId,
    problem,
    setProblem,
    currentQuestion,
    step,
    status,
    rootCause,
    startSession,
    submitAnswer,
    nextStep,
    loading,
    error
  } = useSessionFlow();

  return (
    <div className="app-container">
      <h1>5 Whys Root Cause Analysis</h1>
      {!sessionId && (
        <ProblemInput
          problem={problem}
          onChange={setProblem}
          onSubmit={startSession}
          loading={loading}
        />
      )}
      {error && <div className="error">{error}</div>}
      {sessionId && status !== 'COMPLETED' && (
        <>
          <ProgressIndicator step={step} total={5} />
          {currentQuestion && <QuestionCard question={currentQuestion} />}
          <AnswerForm onSubmit={submitAnswer} disabled={loading} />
          <div className="actions">
            <button onClick={nextStep} disabled={loading || step === 0}>Next</button>
          </div>
        </>
      )}
      {status === 'COMPLETED' && rootCause && (
        <RootCauseView rootCause={rootCause} onRestart={() => window.location.reload()} />
      )}
      <footer className="footer">Session Status: {status || 'IDLE'}</footer>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
