# Detectors D1–D8: what each one does and what it must return

Source: `fault_injection/fi_run.py` (function `run_detectors`) in the v0.2.0 package. Two test patients (`patient01`, `patient02`) with records, a third (`patient20`) for the lockout test, and two doctors are created by the seed block in the same file. A detector **fires** (FAIL) when the weakness is present.

| ID | OWASP | Request sequence | Fires when | Healthy configuration |
|---|---|---|---|---|
| D1 | A07 | log in; `POST /api/auth/logout/` with the refresh token; `POST /api/auth/login/refresh/` with the same token | refresh after logout returns 200 | does not fire (refresh is refused) |
| D1′ | A07 | as D1, but logout is sent with an access token that has expired (lifetime 2 s, request after 3 s) | refresh after logout returns 200 | does not fire (see `d1_experiment/`) |
| D2 | A07 | 12 failed logins for a non-existing user | no 429 among the 12 answers | 429 appears (login scope 5/min) |
| D3 | A07 | 5 failed logins for `patient20`, wait for the throttle window, then the correct password | correct password returns 200 | lockout holds (15 min after 5 failures) |
| D4 | A01 | patient 1 requests `GET /api/records/medical-records/<id>/` of a record that belongs to patient 2; compare both list views | status 200 or non-empty list overlap | 404 and no overlap |
| D5 | A01 | patient `GET /api/auth/users/` (admin endpoint) | status 200 | 403 |
| D6 | A07 | `POST /api/auth/password-reset/` for an existing and a non-existing e-mail | the two answers differ | identical status and body |
| D7 | A02 | `GET /api/auth/me/` and `GET /` | any of X-Content-Type-Options, X-Frame-Options, Content-Security-Policy missing | all three present (set by `nginx.conf`) |
| D8 | A02 | `GET` a non-existing API path, with `Accept: text/html` and `application/json` | body contains a debug page or traceback | plain 404 |

Validity checks: a detector's result is discarded if its precondition fails (e.g. D4 needs at least one record of patient 2; D3 needs the first 5 attempts not to be throttled with 429).

## Applying the detectors to another Django/DRF project
`replication/fi_targets.py` contains the target-agnostic version: per-project adapter (URL prefix, token endpoint, ownership and shared-write oracles, mutation pattern). The pre-registered fault lists for wger and Tandoor are in `FAULTS_PREREGISTERED_*.md` (SHA-256 in the paper, Table 8).
