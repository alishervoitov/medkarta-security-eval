"""Reference app settings.

Faults F1-F8 are switched on with the environment variable REF_FAULT
(for example REF_FAULT=F4, or REF_FAULT=F1,F7). Empty or unset = healthy (BASE).
Every place where a fault changes behaviour is marked with `# FAULT Fn` in the code.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

FAULTS = {f.strip().upper() for f in os.environ.get("REF_FAULT", "").split(",") if f.strip()}

SECRET_KEY = os.environ.get("REF_SECRET_KEY", "reference-app-throwaway-key-not-for-production")
DEBUG = "F8" in FAULTS  # FAULT F8: debug mode on
ALLOWED_HOSTS = os.environ.get("REF_ALLOWED_HOSTS", "127.0.0.1,localhost,testbed.example").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "core",
]
if "F1" not in FAULTS:  # FAULT F1: blacklist app removed -> logout cannot revoke refresh tokens
    INSTALLED_APPS.append("rest_framework_simplejwt.token_blacklist")

MIDDLEWARE = ["core.middleware.SecurityHeadersMiddleware"]  # sets the three headers unless F7

ROOT_URLCONF = "refapp.urls"
AUTH_USER_MODEL = "core.User"
WSGI_APPLICATION = "refapp.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
}]

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.environ.get("REF_DB", str(BASE_DIR / "refapp.sqlite3")),
}}

# Django's default hasher (PBKDF2-SHA256) is kept on purpose, as in the production system.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LOGIN_RATE = "100000/min" if "F2" in FAULTS else "5/min"  # FAULT F2: throttling off
LOCKOUT_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_RATES": {"login": LOGIN_RATE, "password_reset": "5/hour", "logout": "20/min"},
    "UNAUTHENTICATED_USER": None,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}
