# Versions used for the reported results

| Component | Version |
|---|---|
| Python (backend image) | 3.13-slim |
| Django | 6.0.10 |
| Django REST Framework | 3.18.3 |
| djangorestframework-simplejwt | 5.5.1 |
| django-cors-headers / django-redis / celery | 4.9.0 / 7.0.0 / 5.6.3 |
| psycopg | 3.3.4 |
| PostgreSQL / Redis images | postgres:16-alpine / redis:7-alpine |
| Front-end image | node:22-alpine (build), nginx:alpine (serve) |
| OWASP ZAP | ghcr.io/zaproxy/zaproxy:stable (baseline, passive) |
| Bandit / Semgrep (static baseline) | 1.9.4 / 1.181.0 |

Password hashing: Django default (PBKDF2-SHA256, 1,200,000 iterations in Django 6.0); PASSWORD_HASHERS is not overridden in production settings.
Full pin list of the backend (41 packages, exact versions): `requirements.lock.txt` in this folder (copied from the application; it contains no secrets).

## Container images (from `docker images --digests`, 2026-11-14)
The first 12 hex characters of the image digest equal the image ID shown below. The full digest of your own copy is printed by `docker image inspect --format '{{index .RepoDigests 0}}' <image>`.

| Image | Image ID (first 12 hex of digest) | Used for |
|---|---|---|
| postgres:16-alpine | 721873c34ceb | database |
| redis:7-alpine | 858f009f9709 | cache and Celery broker |
| nginx:alpine | 892bb2152464 | front-end proxy (D7 headers) |
| caddy:2-alpine | d8542f48d34a | production only (HTTPS); not part of the test bed |
| ghcr.io/zaproxy/zaproxy:stable | 5ccfff9a4117 | passive ZAP baseline |
| fi-backend:latest | 4aad26ec0f86 | fault-injection copy of the backend, built about three weeks before 2026-11-14 |
| fi-web:latest | 44ac2e2d4c18 | fault-injection copy of the front end |

The backend base image is `python:3.13-slim`; its digest was not recorded, so the `fi-backend` image ID identifies the build that produced the reported results.

## Reference app (`reference_app/`)
Tested with Python 3.13.16, Django 6.0.7, DRF 3.17.1, djangorestframework-simplejwt 5.5.1, SQLite, `runserver --noreload` (see `reference_app/requirements.txt`). These differ slightly from the ShifoSafe versions above (Django 6.0.10, DRF 3.18.3), which is why the reference app pins what it was run with.
