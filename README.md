# MedKarta security evaluation

Reproducibility package for a study of **silently ineffective security controls** in a
small medical-records web application (Django REST Framework, PostgreSQL, React, nginx,
Docker Compose). It contains:

| Path | What it is |
|---|---|
| `oracle_tests/owasp_tests.py` | Stateful, OWASP Top 10 (2025)-oriented test suite (IDOR, role escalation, SQL injection, XSS, JWT, brute force, lockout, headers). Standard library only. |
| `fault_injection/fi_run.py` | Harness that injects 8 controlled faults one at a time into a throw-away copy of the application, rebuilds it, runs 8 detectors (D1-D8) and OWASP ZAP baseline, and writes a detector x fault matrix. |
| `fault_injection/test_mutations.py` | Offline check that each mutation applies to sample code (no Docker needed). |
| `results/fi_results.md` | Results of the run reported in the paper. |

## Faults and detectors

| ID | Fault (control silently disabled) | OWASP | Detector |
|---|---|---|---|
| F1 | Logout does not revoke refresh token (blacklist app removed) | A07 | D1 |
| F2 | Login throttling disabled | A07 | D2 |
| F3 | Account lockout counter never increases | A07 | D3 |
| F4 | Object-level permission removed (IDOR) | A01 | D4 |
| F5 | Admin-only endpoints open to any authenticated user | A01 | D5 |
| F6 | Password reset reveals whether an account exists | A07 | D6 |
| F7 | All nginx security headers removed | A02 | D7 |
| F8 | `DEBUG=True` | A02 | D8 |

## Result (single run)

State-aware tests detected 8/8 faults with 0 false positives on the fault-free baseline.
ZAP baseline (passive, unauthenticated) raised new alerts only for F7. See `results/fi_results.md`.

## Running

Requirements: Linux, Docker with Compose v2, Python 3.9+. The application source is **not**
included; point the harness at your own checkout.

```bash
export MEDKARTA_BACKEND=/path/to/backend   # Django project with docker-compose.prod.yml
export MEDKARTA_FRONTEND=/path/to/frontend
python3 fault_injection/fi_run.py BASE --no-zap   # smoke test, no ZAP
python3 fault_injection/fi_run.py                 # full experiment (about 45 min)
python3 fault_injection/fi_run.py down            # remove the throw-away stack
```

The harness works on a copy (`~/fi_experiment`), runs a separate Compose project (`-p fi`)
and binds only to `127.0.0.1:8081`. It never touches a running deployment.
Seeded accounts use a throw-away password defined in the script; use it only on that copy.

The oracle suite can be run against your own instance:

```bash
BASE=http://127.0.0.1 HOST=your.domain python3 oracle_tests/owasp_tests.py
```

## Limitations

Faults and detectors were written by the same author, so 8/8 shows that the detectors work
and do not interfere with each other; it is not an independent assessment. Each configuration
was run once, with eight faults. ZAP was run in passive, unauthenticated mode only.

Do **not** run these tests against systems you do not own. Code comments and output are in Uzbek.

## License

MIT (see `LICENSE`).
