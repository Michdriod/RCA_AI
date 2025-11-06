# Example: Slow Morning API Latency

Problem:
> Morning API latency spikes between 08:00–09:00 UTC.

Q1: Why does latency spike each morning?  
A1: Because database queries queue longer.

Q2: Why do queries queue longer?  
A2: Because connection pool is saturated at peak.

Q3: Why is the pool saturated?  
A3: Because batch jobs run heavy read queries at 08:00.

Q4: Why do batch jobs run at 08:00?  
A4: Because their cron is aligned with legacy reporting time.

Q5: Why was legacy reporting time kept?  
A5: Because no one reviewed scheduling after traffic growth.

Root Cause Summary:
> Unreviewed batch schedule causing peak-time resource contention.

Contributing Factors:

- Fixed 08:00 cron for batch analytics jobs.
- No periodic job schedule audit process.
- Connection pool size tuned for average load, not peak + batch overlap.

Suggested Actions (illustrative):

- Move batch window to low-traffic hour.
- Implement quarterly job schedule review.
- Reassess pool sizing after schedule change.
