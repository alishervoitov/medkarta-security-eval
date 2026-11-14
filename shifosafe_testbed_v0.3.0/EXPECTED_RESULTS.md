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

## Evidence expected per detector
Faulty state: taken from the run of 2026-10-19 (`results/fi_results.md` in v0.2.0). Healthy state: the condition under which the detector stays silent, as implemented in `DETECTORS.md`.

| Detector | Faulty state (evidence the detector prints) | Healthy state (detector silent) |
|---|---|---|
| D1 | F1: refresh after logout = 200 (logout answered 400, token not blacklisted) | logout 205, refresh after logout 401 |
| D2 | F2: 12 failed attempts all 401, no 429 | at least one 429 among the 12 |
| D3 | F3: correct password after 5 failures = 200 | correct password after 5 failures is refused (not 200) |
| D4 | F4: foreign record GET = 200, list overlap = 4 | foreign record GET = 404, list overlap = 0 |
| D5 | F5: patient GET /api/auth/users/ = 200 | patient GET /api/auth/users/ = 403 |
| D6 | F6: existing e-mail 200, unknown e-mail 404 | same status and same body for both |
| D7 | F7: Content-Security-Policy, X-Content-Type-Options, X-Frame-Options missing (4 new ZAP alerts) | all three present on `/api/auth/me/` and on `/` |
| D8 | F8: debug trace on the 404 page | plain 404 without trace |

## Reference numbers in the paper
* 8 of 8 ShifoSafe faults detected; 16 of 16 informative replication faults detected (wger 4, Tandoor 5, healthcare-backend 6, b2c-system 1); 0 unexpected alarms. Details: `results/replication_results.md`.
* D1 and D1′ on four logout configurations (`d1_experiment/d1_results.jsonl`): D1 is silent on PREFIX and ALLOWANY, D1′ fires on F1, PREFIX and ALLOWANY, neither fires on FIXED.
* Rates and intervals: `d1_experiment/metrics.py` (Clopper–Pearson 95%).

## What a successful reproduction looks like
Run `python3 fi_run.py BASE --no-zap` first. On the healthy configuration every detector must be silent. If any fires, the configuration differs from `env.testbed.example` (check DEBUG, throttle rates, headers) and the experiment should not continue.

## Reference app (open equivalent)
`reference_app/results/reference_results.md` holds the matrix obtained on the open equivalent application (run of 2026-11-14): BASE silent, each of F1–F8 fires exactly its own detector, no other detector fires. The faulty-state evidence is the same as in the ShifoSafe table above. This is a check that the detectors and fault definitions behave as described on an independent code base, not a re-measurement of ShifoSafe.
