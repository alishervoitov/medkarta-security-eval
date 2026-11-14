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
Full pin list of the backend: requirements.txt of the application (not distributed). All pinned versions above were taken from it.
