import { useEffect, useRef } from 'react';

interface PollOptions {
  interval?: number; // base interval ms
  maxAttempts?: number;
  backoffFactor?: number; // multiply interval after each attempt
  enabled?: boolean;
}

export function usePolling(fn: () => Promise<void> | void, deps: any[], options: PollOptions = {}) {
  const { interval = 3000, maxAttempts = Infinity, backoffFactor = 1.4, enabled = true } = options;
  const attemptsRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const currentIntervalRef = useRef(interval);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const tick = async () => {
      attemptsRef.current += 1;
      try {
        await fn();
      } catch {
        // swallow errors; polling shouldn't crash UI
      }
      if (cancelled) return;
      if (attemptsRef.current >= maxAttempts) return;
      currentIntervalRef.current = Math.round(currentIntervalRef.current * backoffFactor);
      timerRef.current = window.setTimeout(tick, currentIntervalRef.current);
    };
    timerRef.current = window.setTimeout(tick, currentIntervalRef.current);
    return () => {
      cancelled = true;
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);
}
