# Reference app: detector matrix (run of 2026-11-14)

Environment: Python 3.13.16, Django 6.0.7, DRF 3.17.1, SimpleJWT 5.5.1, SQLite, `manage.py runserver --noreload`, nine configurations in parallel on 127.0.0.1:8100-8108. Command: `python3 detectors/run_matrix.py` (2 min 40 s). T = detector fires, . = silent.

| Configuration | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | as expected |
|---|---|---|---|---|---|---|---|---|---|
| BASE healthy | . | . | . | . | . | . | . | . | yes |
| F1 logout does not revoke | T | . | . | . | . | . | . | . | yes |
| F2 throttling off | . | T | . | . | . | . | . | . | yes |
| F3 lockout off | . | . | T | . | . | . | . | . | yes |
| F4 IDOR | . | . | . | T | . | . | . | . | yes |
| F5 patient reaches admin endpoint | . | . | . | . | T | . | . | . | yes |
| F6 reset reveals account | . | . | . | . | . | T | . | . | yes |
| F7 headers removed | . | . | . | . | . | . | T | . | yes |
| F8 debug on | . | . | . | . | . | . | . | T | yes |

Evidence printed by the detectors (raw: `matrix_result.json`):

| Detector | Healthy (BASE) | Faulty configuration |
|---|---|---|
| D1 | logout 205, refresh after logout 401 | F1: logout 400, refresh after logout 200 |
| D2 | statuses 401 and 429 | F2: 12 x 401, no 429 |
| D3 | correct password after 5 failures: 403 | F3: 200 |
| D4 | foreign record 404, overlap 0 | F4: 200, overlap 4 |
| D5 | 403 | F5: 200 |
| D6 | 200 / 200 | F6: 200 / 404 |
| D7 | none missing | F7: CSP, X-Content-Type-Options, X-Frame-Options missing |
| D8 | plain 404 | F8: debug trace present |

The faulty-state evidence is identical to that of the ShifoSafe run of 2026-10-19 (`EXPECTED_RESULTS.md`), except that ShifoSafe's lockout answers 4xx with its own status code; the healthy D3 status differs (403 here). This is a property of the equivalent app, not a claim about ShifoSafe.
