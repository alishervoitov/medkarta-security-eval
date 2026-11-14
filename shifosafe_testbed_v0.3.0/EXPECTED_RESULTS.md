# Expected results

## ShifoSafe fault injection (8 faults, run of 2026-10-19). T = detector fires, . = silent
| Configuration | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 |
|---|---|---|---|---|---|---|---|---|
| BASE | . | . | . | . | . | . | . | . |
| F1 logout does not revoke | T | . | . | . | . | . | . | . |
| F2 throttling off | . | T | . | . | . | . | . | . |
| F3 lockout off | . | . | T | . | . | . | . | . |
| F4 IDOR | . | . | . | T | . | . | . | . |
| F5 patient reaches admin endpoint | . | . | . | . | T | . | . | . |
| F6 reset reveals account | . | . | . | . | . | T | . | . |
| F7 headers removed | . | . | . | . | . | . | T | . |
| F8 debug on | . | . | . | . | . | . | . | T |

ZAP baseline (passive): new alerts only for F7 (4 alerts). Run time: about 2 minutes per ZAP scan, about 2 minutes extra for the two 62-second waits of D3.

## Reference numbers in the paper
* 8 of 8 ShifoSafe faults detected; 16 of 16 informative replication faults detected (wger 4, Tandoor 5, healthcare-backend 6, b2c-system 1); 0 unexpected alarms. Details: `results/replication_results.md`.
* D1 and D1′ on four logout configurations (`d1_experiment/d1_results.jsonl`): D1 is silent on PREFIX and ALLOWANY, D1′ fires on F1, PREFIX and ALLOWANY, neither fires on FIXED.
* Rates and intervals: `d1_experiment/metrics.py` (Clopper–Pearson 95%).

## What a successful reproduction looks like
Run `python3 fi_run.py BASE --no-zap` first. On the healthy configuration every detector must be silent. If any fires, the configuration differs from `env.testbed.example` (check DEBUG, throttle rates, headers) and the experiment should not continue.
