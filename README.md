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

## Replication on other Django/DRF projects (`replication/fi_targets.py`)

The detectors were re-implemented as target-agnostic checks (per-target config: URL prefix, token
endpoint, ownership / shared-write oracles, mutation pattern) and run on five projects:

* `healthcare-backend` (third-party, Django 6.1 / DRF 3.18 / simplejwt): all controls present;
  six source/config faults (F1 logout, F2 throttling, F4 IDOR, F5 object permission, F7 headers, F8 DEBUG)
  are injected one at a time. Result: each fault flips exactly its own detector (clean diagonal).
* `TandoorRecipes/recipes` (third-party, Django 5.2 / DRF 3.18, allauth headless session tokens, space-based
  multi-tenancy and guest/user/admin groups; faults pre-registered in `FAULTS_PREREGISTERED_tandoor.md`).
  Five injected faults (rate limiting, two-layer space isolation, two-layer guest write permission, nosniff, DEBUG):
  each flips exactly its own detector. Setup notes: python-ldap omitted; `DJANGO_SETTINGS_MODULE=recipes.settings`.
* `wger` (third-party, Django/DRF + allauth headless JWT + django-axes; faults pre-registered in
  `FAULTS_PREREGISTERED_wger.md` before any run). Deviation: W-F7 is uninformative because wger ships
  without `SecurityMiddleware` (D7 already FAILs on the unmodified code).
* `authorization_api`, `b2c-system` (own projects, same author, similar code base): detectors run on the
  unmodified code (natural findings) plus settings-level repairs and one code fault (b2c-system D4).

Each run uses a throw-away copy, a fresh SQLite DB, an in-memory e-mail backend and `127.0.0.1` only.

    git clone https://github.com/alishervoitov/authorization_api src/authorization_api
    git clone https://github.com/alishervoitov/b2c-system src/b2c-system
    git clone https://github.com/Sumit99589/healthcare-backend src/healthcare-backend
    # venv 1 (Python 3.12): Django==4.1.5 djangorestframework==3.14.0 djangorestframework-simplejwt==5.2.2
    #   drf-yasg==1.21.4 django-cors-headers==3.13.0 django-filter==22.1 django-countries==7.5
    #   django-model-utils==4.3.1 django-dotenv==1.4.2 whitenoise==6.2.0 Pillow requests PyJWT setuptools==69.5.1
    # venv 2 (Python 3.12): pip install -r src/healthcare-backend/requirements.txt requests
    venv/bin/python replication/fi_targets.py --src src --work work --python $PWD/venv/bin/python \
        --py healthcare-backend=$PWD/venv_hc/bin/python

Statuses: PASS (control effective), FAIL (control present but ineffective), ABSENT (no such control),
N/A (not applicable). D7 scores X-Content-Type-Options, X-Frame-Options and Referrer-Policy
(CSP absence is noted, not scored). Results: `results/replication_results.md`.
