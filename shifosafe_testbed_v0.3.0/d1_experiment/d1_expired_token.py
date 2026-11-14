"""
D1 vs D1' on a minimal reconstruction of the logout flaw (Django + DRF + SimpleJWT, SQLite).

D1  (original detector): log in, log out IMMEDIATELY (fresh access token), then refresh.
                         Triggered (= fault noticed) if the refresh still returns 200.
D1' (extended detector): the same, but the access token has EXPIRED before logout
                         (token age is added as a state dimension).
                         Triggered if the refresh token is still usable afterwards.

Configurations (CONFIG env var):
  F1        blacklist app NOT installed, original view          (fault F1 of the paper)
  PREFIX    blacklist app installed, view = IsAuthenticated      (state of the live system at the penetration test)
  ALLOWANY  blacklist app installed, view = AllowAny only        (our first, insufficient fix)
  FIXED     blacklist app installed, view = no authentication    (final fix)
"""
import os, sys, time, json
from datetime import timedelta

CONFIG = os.environ["CONFIG"]
import django
from django.conf import settings

apps = ["django.contrib.auth", "django.contrib.contenttypes", "rest_framework"]
if CONFIG != "F1":
    apps += ["rest_framework_simplejwt.token_blacklist"]
settings.configure(
    DEBUG=False, SECRET_KEY="x" * 50, ROOT_URLCONF=__name__, ALLOWED_HOSTS=["*"],
    INSTALLED_APPS=apps, USE_TZ=True,
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"]},
    SIMPLE_JWT={"ACCESS_TOKEN_LIFETIME": timedelta(seconds=2), "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
                "ROTATE_REFRESH_TOKENS": False},
)
django.setup()

from django.urls import path
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class LogoutBase(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid token."}, status=400)
        return Response(status=205)


class LogoutPrefix(LogoutBase):          # listing in the paper (IsAuthenticated)
    permission_classes = [permissions.IsAuthenticated]


class LogoutAllowAny(LogoutBase):        # permission relaxed, authentication still runs first
    permission_classes = [permissions.AllowAny]


class LogoutFixed(LogoutBase):           # refresh token is the credential
    authentication_classes = []
    permission_classes = [permissions.AllowAny]


VIEW = {"F1": LogoutPrefix, "PREFIX": LogoutPrefix, "ALLOWANY": LogoutAllowAny, "FIXED": LogoutFixed}[CONFIG]
urlpatterns = [
    path("login/", TokenObtainPairView.as_view()),
    path("login/refresh/", TokenRefreshView.as_view()),
    path("logout/", VIEW.as_view()),
]

from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

U = get_user_model()
U.objects.create_user("patient01", password="pw-Test-12345")


def login():
    r = APIClient().post("/login/", {"username": "patient01", "password": "pw-Test-12345"}, format="json")
    assert r.status_code == 200, r.content
    return r.data["access"], r.data["refresh"]


def logout_then_refresh(delay):
    access, refresh = login()
    time.sleep(delay)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Bearer " + access)
    lo = c.post("/logout/", {"refresh": refresh}, format="json").status_code
    rf = APIClient().post("/login/refresh/", {"refresh": refresh}, format="json").status_code
    return lo, rf


lo1, rf1 = logout_then_refresh(0)       # D1: fresh access token
lo2, rf2 = logout_then_refresh(3)       # D1': access token (2 s lifetime) already expired
out = {
    "config": CONFIG,
    "D1": {"logout": lo1, "refresh_after": rf1, "triggered": rf1 == 200},
    "D1prime": {"logout": lo2, "refresh_after": rf2, "triggered": rf2 == 200},
}
print(json.dumps(out))
