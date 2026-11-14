# Reference app: an open, equivalent security layer for re-running F1-F8

ShifoSafe's source is closed. This folder is a small, complete Django/DRF application written for the test bed. It reproduces the **security-relevant behaviour** that detectors D1-D8 exercise, with the same URLs and the same kinds of responses, and it can be switched into each of the eight faults F1-F8 with one environment variable. It lets a reviewer run the whole fault-injection experiment (healthy run, eight faulty runs) in a few minutes without any ShifoSafe code.

**What it is not.** It is not ShifoSafe, and a result obtained here is not a re-measurement of ShifoSafe: the application is an equivalent (about 250 lines), written after the ShifoSafe experiment, to show that the detectors and the fault definitions work as described on an independent code base. Differences are listed below.

## Run (about 3 minutes)
```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 detectors/run_matrix.py
```
`run_matrix.py` creates a throw-away SQLite database per configuration, migrates, seeds the synthetic accounts (`seed_testdata`), starts the server on 127.0.0.1 (ports 8100+), runs D1-D8 and prints the matrix. Exit code 0 means every configuration gave the expected result. Selected configurations: `python3 detectors/run_matrix.py BASE F4`.

Manual use:
```
export REF_DB=/tmp/ref.sqlite3 REF_FAULT=F4      # empty REF_FAULT = healthy
python3 manage.py migrate && python3 manage.py seed_testdata
python3 manage.py runserver --noreload 127.0.0.1:8000
python3 detectors/run_detectors.py http://127.0.0.1:8000
```
The detectors are target-agnostic: `run_detectors.py` can be pointed at any instance that exposes the same endpoints.

## Faults (each is marked `# FAULT Fn` in the code)
| Fault | Where | Change |
|---|---|---|
| F1 | `refapp/settings.py` | `token_blacklist` app not installed, so logout cannot revoke the refresh token |
| F2 | `refapp/settings.py` | login throttle rate 5/min -> 100000/min |
| F3 | `core/views.py` | failed-attempt counter increases by 0 instead of 1 |
| F4 | `core/permissions.py`, `core/views.py` | owner check and owner filter removed |
| F5 | `core/views.py` | `/api/auth/users/` open to any authenticated user instead of admins |
| F6 | `core/views.py` | password reset answers 404 for an unknown e-mail |
| F7 | `core/middleware.py` | three security headers not set |
| F8 | `refapp/settings.py` | `DEBUG = True` |

## Endpoints
`POST /api/auth/login/`, `POST /api/auth/login/refresh/`, `POST /api/auth/logout/`, `GET /api/auth/me/`, `GET /api/auth/users/` (admin), `POST /api/auth/password-reset/`, `GET /api/records/medical-records/` and `.../<id>/`, `GET /`.

## Differences from ShifoSafe (stated so that the result is not over-read)
- Refresh token is sent in the JSON body here; ShifoSafe uses an HttpOnly cookie with a CSRF header. D1 logic is the same (refresh after logout).
- Security headers come from a Django middleware here; ShifoSafe sets them in nginx (`nginx.conf` in the parent folder).
- SQLite and an in-process cache here; PostgreSQL and Redis in ShifoSafe. Run one server process (as `run_matrix.py` does) because the throttle counters live in process memory.
- The lockout answers 403 here; ShifoSafe's status code differs. Detectors test "not 200", so the outcome is the same.
- No frontend, no Celery, no e-mail sending (password reset only returns the response that D6 compares).
- Password hashing is Django's default PBKDF2-SHA256, as in production. Logins therefore take a few hundred milliseconds.
- Not run here: ZAP (passive scan) and Docker. The Docker/ZAP path of the parent folder is separate and was not exercised against this app.

## Tested with
Python 3.13.16, Django 6.0.7, DRF 3.17.1, djangorestframework-simplejwt 5.5.1 (see `requirements.txt`). Result of the run: `results/reference_results.md`, `results/matrix_result.json`.

## Safety
Local use only (127.0.0.1). The secret key and the test password in the code are throw-away values for the synthetic data; never reuse them or deploy this app.
