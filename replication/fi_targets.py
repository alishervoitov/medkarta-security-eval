#!/usr/bin/env python3
"""Config-driven replication of the MedKarta security-control detectors on other Django/DRF projects.

For every (target, condition) the harness
  1. copies the project source into an isolated work dir (never uses the repo's db.sqlite3),
  2. optionally applies a source mutation (fault injection),
  3. writes a settings overlay (fresh SQLite DB, locmem e-mail, 127.0.0.1 only, optional repairs),
  4. migrates, seeds users, starts runserver on 127.0.0.1:<port>,
  5. runs detectors D1..D8 (+ target-specific observations X1, X2),
  6. stops the server and writes a markdown / JSON report.

Statuses: PASS (control effective), FAIL (control present/observable but ineffective),
          ABSENT (no such control in the target), N/A (not applicable / not reachable).
"""
import argparse, json, os, shutil, signal, socket, subprocess, sys, time

import requests

PW = lambda n: "Pw-%s-12345!" % n

TARGETS = {
    "authorization_api": {
        "settings": "registration_api.settings",
        "prefix": "/auth/user/",
        "reset": "send-reset-password/",
        "logout": None,
        "token_path": None,
        "cart": None,
        "seed_extra": "",
        "overlay": True,
        "verification": True,
        "register_body": "legacy",
    },
    "b2c-system": {
        "settings": "B2C.settings",
        "prefix": "/auth/",
        "reset": "send-email/",
        "logout": None,
        "token_path": "/api/token-obtain-pair-view/",
        "overlay": True,
        "verification": True,
        "register_body": "legacy",
        "cart": {"list": "/order/cart-item/", "add": "/order/add-item/", "product_id": 1},
        "seed_extra": (
            "from product.models import Product\n"
            "Product.objects.create(name='p',price=1,quantity=5,medicine_form='x',country='UZBEKISTAN',"
            "company='c',trade_name_of_the_drug='t',composition='c',pharmacotherapeutic_group='g',"
            "contraindication='c',pharmacokinetic='p',storage_condition='s',expiration='e')\n"
        ),
    },
    "healthcare-backend": {
        "settings": "config.settings",
        "overlay": False,
        "prefix": "/api/auth/",
        "reset": None,
        "logout": {"path": "/api/auth/logout/", "refresh": "/api/auth/token/refresh/"},
        "token_path": None,
        "cart": None,
        "cool": True,
        "verification": False,
        "register_body": "healthcare",
        "headers_path": "/api/health/",
        "owned": {"create": "/api/patients/", "detail": "/api/patients/%d/",
                  "body": {"name": "P1", "date_of_birth": "1990-01-01", "gender": "male", "phone": "+91 98765 43210"}},
        "shared_write": {"create": "/api/doctors/", "detail": "/api/doctors/%d/",
                         "body": {"name": "D1", "specialization": "cardiology", "license_number": "L-1",
                                  "email": "d1@fi.test", "phone": "+91 98765 43210"},
                         "patch": {"hospital": "HACKED"}},
        "seed_extra": "",
        "seed_name_kw": "name",
    },
    "tandoor": {
        "dir": "recipes",
        "settings": "recipes.settings",
        "overlay": False,
        "kind": "tandoor",
        "prefix": "",
        "reset": None,
        "login_path": "/_allauth/app/v1/auth/login",
        "login_user_key": "username",
        "token_path": None,
        "auth_header": "X-Session-Token",
        "token_cache": True,
        "login_gap": 25,
        "logout": {"kind": "session_check", "path": "/_allauth/app/v1/auth/session", "check": "/api/recipe/",
                   "actor": "dave"},
        "cart": None,
        "cool": False,
        "verification": False,
        "no_register": True,
        "headers_path": "/api/server-settings/current",
        "debug_path": "/_allauth/app/v1/fi-no-such-path",
        "lockout_after": 12,
        "owned": {"create": "/api/recipe/", "detail": "/api/recipe/%d/", "list": "/api/recipe/",
                  "other": "carol", "body": {"name": "R1", "description": "d", "steps": [{"instruction": "mix", "ingredients": []}], "keywords": [], "working_time": 1, "waiting_time": 1, "servings": 1}},
        "shared_write": {"create": "/api/recipe/", "detail": "/api/recipe/%d/", "body": {"name": "R1", "description": "d", "steps": [{"instruction": "mix", "ingredients": []}], "keywords": [], "working_time": 1, "waiting_time": 1, "servings": 1},
                         "other": "bob", "patch": {"description": "HACKED"}},
        "seed_extra": "",
    },
    "wger": {
        "settings": "settings.main",
        "overlay": False,
        "kind": "wger",
        "prefix": "",
        "reset": None,
        "login_path": "/allauth/app/v1/auth/login",
        "login_user_key": "username",
        "token_path": None,
        "logout": {"kind": "session_delete", "path": "/allauth/app/v1/auth/session", "ok": [200, 204, 401],
                   "refresh": "/allauth/app/v1/tokens/refresh", "refresh_key": "refresh_token", "refresh_ok": 200},
        "cart": None,
        "cool": False,
        "verification": False,
        "no_register": True,
        "headers_path": "/api/v2/version/",
        "lockout_after": 12,
        "owned": {"create": "/api/v2/routine/", "detail": "/api/v2/routine/%d/", "list": "/api/v2/routine/",
                  "body": {"name": "R1", "description": "d", "start": "2026-01-01", "end": "2026-02-01"}},
        "shared_write": {"create": "/api/v2/routine/", "detail": "/api/v2/routine/%d/",
                         "body": {"name": "T1", "description": "d", "start": "2026-01-01", "end": "2026-02-01",
                                  "is_public": True, "is_template": True},
                         "patch": {"description": "HACKED"}},
        "fixtures": ["languages", "groups", "licenses", "setting_repetition_units", "setting_weight_units"],
        "seed_extra": "",
    },
}

# condition -> overlay switches and optional source mutation
CONDITIONS = {
    "authorization_api": [
        {"name": "BASE", "debug": True, "throttle": False, "mutation": None},
        {"name": "REPAIR", "debug": False, "throttle": True, "mutation": None},
    ],
    "b2c-system": [
        {"name": "BASE", "debug": True, "throttle": False, "mutation": None},
        {"name": "REPAIR", "debug": False, "throttle": True, "mutation": None},
        {"name": "FAULT_D4", "debug": False, "throttle": True,
         "mutation": ("zakaz/views.py", "return OrderDetail.objects.filter(user=user)\n",
                      "return OrderDetail.objects.all()\n")},
    ],
    "tandoor": [
        {"name": "BASE", "debug": False, "throttle": False, "mutation": None},
        {"name": "T_F2_ratelimit_off", "debug": False, "throttle": False,
         "mutations": [("append", "recipes/settings.py", "ACCOUNT_RATE_LIMITS = False")]},
        {"name": "T_F4_space_isolation", "debug": False, "throttle": False,
         "mutations": [
             ("cookbook/helper/scope_middleware.py",
              "                                with scope(space=request.space):",
              "                                with scopes_disabled():"),
             ("cookbook/views/api.py",
              "            space=self.request.space).filter(\n            Q(private=False)",
              "            pk__gt=0).filter(\n            Q(private=False)")]},
        {"name": "T_F5_guest_write", "debug": False, "throttle": False,
         "mutations": [("all", "cookbook/helper/permission_helper.py",
                        "has_group_permission(request, ['guest']) and request.method in SAFE_METHODS",
                        "has_group_permission(request, ['guest'])")]},
        {"name": "T_F7_headers", "debug": False, "throttle": False,
         "mutations": [("append", "recipes/settings.py", "SECURE_CONTENT_TYPE_NOSNIFF = False")]},
        {"name": "T_F8_debug", "debug": True, "throttle": False, "mutation": None},
    ],
    "wger": [
        {"name": "BASE", "debug": False, "throttle": False, "mutation": None},
        {"name": "W_F2_axes_off", "debug": False, "throttle": False, "mutation": None, "env": {"AXES_ENABLED": "0"}},
        {"name": "W_F4_idor", "debug": False, "throttle": False,
         "mutation": ("wger/manager/api/views.py",
                      "request_user_or_trainer_q(request=self.request) | Q(is_public=True)", "Q()")},
        {"name": "W_F5_objperm", "debug": False, "throttle": False,
         "mutation": ("wger/manager/api/permissions.py",
                      "return request.method in permissions.SAFE_METHODS", "return True")},
        {"name": "W_F7_headers", "debug": False, "throttle": False,
         "mutation": ("append", "settings/main.py", "SECURE_CONTENT_TYPE_NOSNIFF = False")},
        {"name": "W_F8_debug", "debug": True, "throttle": False, "mutation": None},
    ],
    "healthcare-backend": [
        {"name": "BASE", "debug": False, "throttle": False, "mutation": None},
        {"name": "F1_logout", "debug": False, "throttle": False,
         "mutation": ("apps/accounts/views.py", "        token.blacklist()\n", "        pass\n")},
        {"name": "F2_throttle", "debug": False, "throttle": False,
         "mutation": ("apps/accounts/views.py", "throttle_classes = [ScopedRateThrottle]", "throttle_classes = []")},
        {"name": "F4_idor", "debug": False, "throttle": False,
         "mutation": ("apps/patients/views.py", "return Patient.objects.filter(created_by=self.request.user)",
                      "return Patient.objects.all()")},
        {"name": "F5_objperm", "debug": False, "throttle": False,
         "mutation": ("apps/common/permissions.py",
                      "return request.user.is_staff or obj.created_by_id == request.user.id", "return True")},
        {"name": "F7_headers", "debug": False, "throttle": False,
         "mutation": ("config/settings.py", "SECURE_CONTENT_TYPE_NOSNIFF = True", "SECURE_CONTENT_TYPE_NOSNIFF = False")},
        {"name": "F8_debug", "debug": True, "throttle": False, "mutation": None},
    ],
}

OVERLAY = '''import os
from {settings} import *
DEBUG = os.environ.get("FI_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
DATABASES = {{"default": {{"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ["FI_DB"]}}}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
if os.environ.get("FI_THROTTLE") == "1":
    REST_FRAMEWORK = dict(REST_FRAMEWORK)
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ["rest_framework.throttling.AnonRateThrottle"]
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {{"anon": "30/min"}}
'''

SEED = '''from django.contrib.auth import get_user_model
U = get_user_model()
for n in ("alice", "bob", "carol", "dave"):
    u = U.objects.create_user(%s)
    print("ID:%%s:%%s" %% (n, u.pk))
'''


SEED_TANDOOR = '''from django.contrib.auth.models import User, Group
from allauth.account.models import EmailAddress
from django_scopes import scopes_disabled
from cookbook.models import UserSpace
from cookbook.helper.permission_helper import create_space_for_user
spaces = {}
for n in ("alice", "bob", "carol", "dave"):
    u = User.objects.create_user(username=n, email=n + "@fi.test", password="Pw-" + n + "-12345!")
    EmailAddress.objects.create(user=u, email=u.email, verified=True, primary=True)
    if n != "bob":
        spaces[n] = create_space_for_user(u, name=n + "-space")
    print("ID:%s:%s" % (n, u.pk))
with scopes_disabled():
    x = UserSpace.objects.create(user=User.objects.get(username="bob"), space=spaces["alice"].space, active=True)
    x.groups.add(Group.objects.get(name="guest"))
'''

SEED_WGER = '''from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
U = get_user_model()
for n in ("alice", "bob", "carol", "dave"):
    u = U.objects.create_user(username=n, email=n + "@fi.test", password="Pw-" + n + "-12345!")
    EmailAddress.objects.create(user=u, email=u.email, verified=True, primary=True)
    print("ID:%s:%s" % (n, u.pk))
'''


# ----------------------------------------------------------------------------- helpers
def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], str):
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r:
                return r
    return None


def jbody(r):
    try:
        return r.json()
    except Exception:
        return None


def port_open(port):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class Run:
    def __init__(self, target, cond, args, port):
        self.t, self.c, self.a, self.port = TARGETS[target], cond, args, port
        self.target = target
        self.dir = os.path.join(args.work, "%s__%s" % (target, cond["name"]))
        self.base = "http://127.0.0.1:%d" % port
        self.env = None
        self.proc = None
        self.ids = {}
        self.log = None

    # -- preparation
    def prepare(self):
        src = os.path.join(self.a.src, self.t.get("dir", self.target))
        shutil.rmtree(self.dir, ignore_errors=True)
        shutil.copytree(src, self.dir, ignore=shutil.ignore_patterns(".git", ".idea", "db.sqlite3", "__pycache__"))
        muts = self.c.get("mutations") or ([self.c["mutation"]] if self.c.get("mutation") else [])
        for m in muts:
            if m[0] == "append":
                open(os.path.join(self.dir, m[1]), "a", encoding="utf-8").write("\n" + m[2] + "\n")
                continue
            replace_all = m[0] == "all"
            f, old, new = (m[1], m[2], m[3]) if replace_all else (m[0], m[1], m[2])
            path = os.path.join(self.dir, f)
            text = open(path, encoding="utf-8").read()
            if text.count(old) < 1:
                raise RuntimeError("mutation pattern not found in %s: %r" % (f, old))
            open(path, "w", encoding="utf-8").write(text.replace(old, new) if replace_all else text.replace(old, new, 1))
        db = os.path.join(self.dir, "fi.sqlite3")
        if self.t.get("overlay"):
            open(os.path.join(self.dir, "fi_overlay.py"), "w").write(OVERLAY.format(settings=self.t["settings"]))
            self.env = dict(os.environ, DJANGO_SETTINGS_MODULE="fi_overlay", FI_DB=db,
                            FI_DEBUG="1" if self.c["debug"] else "0",
                            FI_THROTTLE="1" if self.c["throttle"] else "0", PYTHONDONTWRITEBYTECODE="1")
        elif self.t.get("kind") == "tandoor":
            self.env = dict(os.environ, DJANGO_SETTINGS_MODULE=self.t["settings"], DATABASE_URL="sqlite://localhost/" + db,
                            SECRET_KEY="fi-test-secret-key-not-used-anywhere-else-0123456789abcdef",
                            DEBUG="1" if self.c["debug"] else "0", ALLOWED_HOSTS="127.0.0.1,localhost",
                            PYTHONDONTWRITEBYTECODE="1", **self.c.get("env", {}))
        elif self.t.get("kind") == "wger":
            self.env = dict(os.environ, DJANGO_SETTINGS_MODULE=self.t["settings"],
                            DJANGO_DB_ENGINE="django.db.backends.sqlite3", DJANGO_DB_DATABASE=db,
                            SECRET_KEY="fi-test-secret-key-not-used-anywhere-else-0123456789abcdef",
                            DJANGO_DEBUG="1" if self.c["debug"] else "0", PYTHONDONTWRITEBYTECODE="1",
                            **self.c.get("env", {}))
        else:  # the project is configured through environment variables
            self.env = dict(os.environ, DJANGO_SETTINGS_MODULE=self.t["settings"],
                            DJANGO_SECRET_KEY="fi-test-secret-key-not-used-anywhere-else-0123456789",
                            DJANGO_DEBUG="1" if self.c["debug"] else "0",
                            DATABASE_URL="sqlite:///" + db, PYTHONDONTWRITEBYTECODE="1")

    def py(self):
        return self.a.py.get(self.target, self.a.python)

    def manage(self, *cmd, timeout=180):
        return subprocess.run([self.py(), "manage.py", *cmd], cwd=self.dir, env=self.env,
                              capture_output=True, text=True, timeout=timeout)

    def setup(self):
        r = self.manage("migrate", "--noinput")
        if r.returncode:
            raise RuntimeError("migrate failed:\n" + r.stdout[-800:] + r.stderr[-1500:])
        if self.t.get("kind") == "tandoor":
            r = self.manage("shell", "-c", SEED_TANDOOR)
            if r.returncode:
                raise RuntimeError("seed failed:\n" + r.stderr[-1500:])
            for line in r.stdout.splitlines():
                if line.startswith("ID:"):
                    _, n, i = line.split(":")
                    self.ids[n] = int(i)
            return self._start()
        if self.t.get("kind") == "wger":
            if self.manage("loaddata", *self.t["fixtures"]).returncode:
                raise RuntimeError("loaddata failed")
            kr = self.manage("generate-jwt-keys")
            for line in kr.stdout.splitlines():
                if line.startswith(("JWT_PRIVATE_KEY=", "JWT_PUBLIC_KEY=")):
                    k, v = line.split("=", 1)
                    self.env[k] = v.strip()
            r = self.manage("shell", "-c", SEED_WGER)
            if r.returncode:
                raise RuntimeError("seed failed:\n" + r.stderr[-1500:])
            for line in r.stdout.splitlines():
                if line.startswith("ID:"):
                    _, n, i = line.split(":")
                    self.ids[n] = int(i)
            return self._start()
        kw = ('email=n + "@fi.test", password="Pw-" + n + "-12345!", name=n' if self.t.get("seed_name_kw") else
              'username=n, email=n + "@fi.test", password="Pw-" + n + "-12345!", full_name=n, country="UZBEKISTAN", '
              'user_type="Customer", phone_number="1", is_verified=True')
        r = self.manage("shell", "-c", (SEED % kw) + self.t["seed_extra"])
        if r.returncode:
            raise RuntimeError("seed failed:\n" + r.stderr[-1500:])
        for line in r.stdout.splitlines():
            if line.startswith("ID:"):
                _, n, i = line.split(":")
                self.ids[n] = int(i)
        return self._start()

    def _start(self):
        self.log = open(os.path.join(self.dir, "server.log"), "w")
        self.proc = subprocess.Popen([self.py(), "manage.py", "runserver", "127.0.0.1:%d" % self.port, "--noreload"],
                                     cwd=self.dir, env=self.env, stdout=self.log, stderr=subprocess.STDOUT,
                                     preexec_fn=os.setsid)
        for _ in range(300):
            if port_open(self.port):
                return
            if self.proc.poll() is not None:
                break
            time.sleep(0.3)
        raise RuntimeError("server did not start; see " + self.log.name)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            try:
                self.proc.wait(10)
            except Exception:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
        if self.log:
            self.log.close()

    # -- http helpers
    def url(self, p):
        return self.base + p

    def app(self, p):
        return self.url(self.t["prefix"] + p)

    def login(self, name, password=None):
        if self.t.get("login_path"):
            ident = name if self.t.get("login_user_key") == "username" else name + "@fi.test"
            return requests.post(self.url(self.t["login_path"]),
                                 json={self.t.get("login_user_key", "email"): ident, "password": password or PW(name)}, timeout=30)
        return requests.post(self.app("login/"), json={"email": name + "@fi.test", "password": password or PW(name)}, timeout=15)

    def tokens(self, name):
        if self.t.get("token_cache") and name in getattr(self, "_tok", {}):
            return self._tok[name]
        if self.t.get("login_gap"):
            wait = getattr(self, "_last_login", 0) + self.t["login_gap"] - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last_login = time.time()
        res = self._tokens(name)
        if self.t.get("token_cache"):
            self.__dict__.setdefault("_tok", {})[name] = res
        return res

    def _tokens(self, name):
        if self.t["token_path"]:
            r = requests.post(self.url(self.t["token_path"]), json={"email": name + "@fi.test", "password": PW(name)}, timeout=15)
        else:
            r = self.login(name)
        b = jbody(r)
        return ((find_key(b, "access") or find_key(b, "access_token") or find_key(b, "session_token")),
                (find_key(b, "refresh") or find_key(b, "refresh_token")))

    def hdr(self, tok):
        if self.t.get("auth_header"):
            return {self.t["auth_header"]: tok or ""}
        return {"Authorization": "Bearer " + tok}

    # -- detectors ------------------------------------------------------------
    def cool(self, sec=63):
        if self.t.get("cool"):
            time.sleep(sec)  # let a per-minute throttle window expire so detectors do not interfere

    def d1(self):
        lg = self.t["logout"]
        if not lg:
            acc, ref = self.tokens("alice")
            r = requests.post(self.url("/api/refresh-token/"), json={"refresh": ref}, timeout=15)
            return "ABSENT", "no logout endpoint; refresh token stays usable (refresh=%s)" % r.status_code
        if lg.get("kind") == "session_check":
            tok, _ = self.tokens(lg["actor"])
            pre = requests.get(self.url(lg["check"]), headers=self.hdr(tok), timeout=30)
            if pre.status_code != 200:
                return "N/A", "session token not accepted before logout (%d); oracle inconclusive" % pre.status_code
            lo = requests.delete(self.url(lg["path"]), headers=self.hdr(tok), timeout=30)
            post = requests.get(self.url(lg["check"]), headers=self.hdr(tok), timeout=30)
            return ("FAIL" if post.status_code == 200 else "PASS"), "logout=%d; same session token after logout -> %d (expected 401/403)" % (
                lo.status_code, post.status_code)
        if lg.get("kind") == "session_delete":
            meta = (jbody(self.login("carol")) or {}).get("meta", {})
            ses, ref = meta.get("session_token"), meta.get("refresh_token")
            lo = requests.delete(self.url(lg["path"]), headers={"X-Session-Token": ses or ""}, timeout=30)
            rf = requests.post(self.url(lg["refresh"]), json={lg["refresh_key"]: ref}, timeout=30)
            return ("FAIL" if rf.status_code == lg["refresh_ok"] else "PASS"), (
                "logout=%d (accepted codes %s); refresh after logout=%d (expected rejection)" % (lo.status_code, lg["ok"], rf.status_code))
        acc, ref = self.tokens("carol")
        lo = requests.post(self.url(lg["path"]), json={"refresh": ref}, headers=self.hdr(acc), timeout=15)
        rf = requests.post(self.url(lg["refresh"]), json={"refresh": ref}, timeout=15)
        return ("FAIL" if rf.status_code == 200 else "PASS"), "logout=%d; refresh after logout=%d (expected 401)" % (
            lo.status_code, rf.status_code)

    def d2(self):
        codes = [self.login("dave", "wrong-%d" % i).status_code for i in range(40)]
        n429 = codes.count(429)
        st = "PASS" if n429 else "FAIL"
        return st, "40 failed logins -> 429 x%d, others %s" % (n429, sorted(set(c for c in codes if c != 429)))

    def d3(self):
        self.cool()
        n = self.t.get("lockout_after", 6)
        for i in range(n):
            self.login("carol", "wrong-%d" % i)
        r = self.login("carol")
        if r.status_code == 429:
            self.cool()
            r = self.login("carol")
        ok = r.status_code == 200
        return ("FAIL" if ok else "PASS"), "correct password after %d failures -> %d" % (n, r.status_code)

    def d4(self):
        c, o = self.t["cart"], self.t.get("owned")
        other = (o or {}).get("other", "bob")
        a_acc, _ = self.tokens("alice")
        b_acc, _ = self.tokens(other)
        if c:
            ra = requests.post(self.url(c["add"]), json={"product_id": c["product_id"]}, headers=self.hdr(a_acc), timeout=15)
            lst = requests.get(self.url(c["list"]), headers=self.hdr(b_acc), timeout=15)
            body = jbody(lst)
            items = body.get("results", body) if isinstance(body, dict) else body
            n = len(items) if isinstance(items, list) else -1
            return ("FAIL" if n != 0 else "PASS"), "alice add-item=%d; bob lists cart -> %d item(s) (expected 0)" % (ra.status_code, n)
        if o:
            ra = requests.post(self.url(o["create"]), json=o["body"], headers=self.hdr(a_acc), timeout=15)
            rid = (jbody(ra) or {}).get("id")
            if not rid:
                return "N/A", "could not create the owned record (%d): %s" % (ra.status_code, ra.text[:120])
            rb = requests.get(self.url(o["detail"] % rid), headers=self.hdr(b_acc), timeout=15)
            in_list = False
            if o.get("list"):
                rl = jbody(requests.get(self.url(o["list"]), headers=self.hdr(b_acc), timeout=15))
                items = rl.get("results", rl) if isinstance(rl, dict) else rl
                in_list = isinstance(items, list) and any(isinstance(x, dict) and x.get("id") == rid for x in items)
            leak = rb.status_code == 200 or in_list
            return ("FAIL" if leak else "PASS"), "alice creates record %s; %s GET it -> %d, record in %s's list: %s (expected 404/403, absent)" % (
                rid, other, rb.status_code, other, in_list)
        bob_id = self.ids["bob"]
        notes = []
        for p in ("edit-profile/", "edit-profile/%d/" % bob_id):
            r = requests.put(self.app(p), json={"full_name": "HACKED"}, headers=self.hdr(a_acc), timeout=15)
            notes.append("PUT %s -> %d" % (p, r.status_code))
        pr = requests.get(self.app("user_profile/"), headers=self.hdr(b_acc), timeout=15)
        name = (jbody(pr) or {}).get("full_name")
        return ("FAIL" if name == "HACKED" else "PASS"), "; ".join(notes) + "; bob.full_name=%r" % name

    def d5(self):
        w = self.t.get("shared_write")
        if not w:
            return "N/A", "no shared record with owner-only write access in the target"
        a_acc, _ = self.tokens("alice")
        b_acc, _ = self.tokens(w.get("other", "bob"))
        ra = requests.post(self.url(w["create"]), json=w["body"], headers=self.hdr(a_acc), timeout=15)
        rid = (jbody(ra) or {}).get("id")
        if not rid:
            return "N/A", "could not create the shared record (%d): %s" % (ra.status_code, ra.text[:120])
        rb = requests.patch(self.url(w["detail"] % rid), json=w["patch"], headers=self.hdr(b_acc), timeout=15)
        return ("FAIL" if rb.status_code == 200 else "PASS"), "alice creates record %s; %s PATCH it -> %d (expected 403)" % (rid, w.get("other", "bob"), rb.status_code)

    def d6(self):
        path = self.t["reset"]
        if not path:
            return "N/A", "no password-reset endpoint"
        r1 = requests.post(self.app(path), json={"email": "alice@fi.test"}, timeout=15)
        r2 = requests.post(self.app(path), json={"email": "nobody@fi.test"}, timeout=15)
        differ = r1.status_code != r2.status_code
        return ("FAIL" if differ else "PASS"), "existing e-mail -> %d, unknown e-mail -> %d" % (r1.status_code, r2.status_code)

    def d7(self):
        r = requests.get(self.url(self.t.get("headers_path", "/")), timeout=15)
        need = ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]
        missing = [h for h in need if h not in r.headers]
        note = "" if "Content-Security-Policy" in r.headers else " (CSP absent, noted but not scored)"
        return ("FAIL" if missing else "PASS"), "missing: %s%s" % (", ".join(missing) or "none", note)

    def d8(self):
        r = requests.get(self.url(self.t.get("debug_path", "/fi-no-such-path/")), timeout=30)
        leak = "DEBUG = True" in r.text or "Using the URLconf" in r.text
        return ("FAIL" if leak else "PASS"), "404 page -> %d, debug trace %s" % (r.status_code, "present" if leak else "absent")

    # target-specific observations (not part of the D1-D8 matrix)
    def x1_x2(self):
        if self.t.get("no_register"):
            return ("N/A", "registration not exercised for this target"), ("N/A", "registration not exercised for this target")
        if self.t["register_body"] == "healthcare":
            body = {"name": "zed", "email": "zed@fi.test", "password": "Pw-zed-12345!"}
        else:
            body = {"username": "zed", "full_name": "z", "email": "zed@fi.test", "password": "Pw-zed-12345!",
                    "password1": "Pw-zed-12345!", "country": "UZBEKISTAN", "company_name": "c",
                    "user_type": "Customer", "phone_number": "1", "corporate_number": "1"}
        r = requests.post(self.app("register/"), json=body, timeout=15)
        acc = find_key(jbody(r), "access")
        if not self.t["verification"]:
            x1 = ("N/A", "target has no e-mail verification step")
        elif acc:
            pr = requests.get(self.app("user_profile/"), headers=self.hdr(acc), timeout=15)
            x1 = ("FAIL" if pr.status_code == 200 else "PASS", "unverified user's token on user_profile -> %d" % pr.status_code)
        else:
            x1 = ("PASS", "register -> %d, no token returned" % r.status_code)
        echoed = "Pw-zed-12345!" in r.text
        x2 = ("FAIL" if echoed else "PASS", "plaintext password %s in register response (%d)" % ("echoed" if echoed else "not present", r.status_code))
        return x1, x2

    def run_all(self):
        res = {}
        for k in ("d8", "d7", "d6"):
            res[k.upper()] = getattr(self, k)()
        x1, x2 = self.x1_x2()
        res["X1"], res["X2"] = x1, x2
        for k in ("d1", "d5", "d4", "d3", "d2"):  # D3 cools down first; D2 last: it sends a burst of anonymous requests
            res[k.upper()] = getattr(self, k)()
        return res


EXPECT = {  # sanity oracle for the harness itself: condition -> {detector: status}
    ("authorization_api", "BASE"): {"D2": "FAIL", "D8": "FAIL"},
    ("authorization_api", "REPAIR"): {"D2": "PASS", "D8": "PASS"},
    ("b2c-system", "BASE"): {"D2": "FAIL", "D8": "FAIL", "D4": "PASS"},
    ("b2c-system", "REPAIR"): {"D2": "PASS", "D8": "PASS", "D4": "PASS"},
    ("b2c-system", "FAULT_D4"): {"D2": "PASS", "D8": "PASS", "D4": "FAIL"},
}
_ALL6 = {"D1": "PASS", "D2": "PASS", "D4": "PASS", "D5": "PASS", "D7": "PASS", "D8": "PASS"}
for _c, _d in (("BASE", None), ("F1_logout", "D1"), ("F2_throttle", "D2"), ("F4_idor", "D4"),
               ("F5_objperm", "D5"), ("F7_headers", "D7"), ("F8_debug", "D8")):
    EXPECT[("healthcare-backend", _c)] = dict(_ALL6, **({_d: "FAIL"} if _d else {}))


_T = {"D1": "PASS", "D2": "PASS", "D3": "PASS", "D4": "PASS", "D5": "PASS", "D7": "PASS", "D8": "PASS"}
for _c, _d in (("BASE", {}), ("T_F2_ratelimit_off", {"D2": "FAIL", "D3": "FAIL"}), ("T_F4_space_isolation", {"D4": "FAIL"}),
               ("T_F5_guest_write", {"D5": "FAIL"}), ("T_F7_headers", {"D7": "FAIL"}), ("T_F8_debug", {"D8": "FAIL"})):
    EXPECT[("tandoor", _c)] = dict(_T, **_d)
_W = {"D1": "PASS", "D2": "PASS", "D3": "PASS", "D4": "PASS", "D5": "PASS", "D8": "PASS"}  # D7 pre-registered as "report as found"
for _c, _d in (("BASE", {}), ("W_F2_axes_off", {"D2": "FAIL", "D3": "FAIL"}), ("W_F4_idor", {"D4": "FAIL"}),
               ("W_F5_objperm", {"D5": "FAIL"}), ("W_F7_headers", {"D7": "FAIL"}), ("W_F8_debug", {"D8": "FAIL"})):
    EXPECT[("wger", _c)] = dict(_W, **_d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="dir containing the cloned target repos")
    ap.add_argument("--work", required=True, help="scratch dir for isolated copies")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--out", default="targets_results")
    ap.add_argument("--only", default=None)
    ap.add_argument("--cond", default=None, help="run only this condition name")
    ap.add_argument("--py", action="append", default=[], help="target=path/to/python (per-target interpreter)")
    ap.add_argument("--port0", type=int, default=18101)
    args = ap.parse_args()
    args.py = dict(x.split("=", 1) for x in args.py)
    args.src, args.work = os.path.abspath(args.src), os.path.abspath(args.work)
    os.makedirs(args.work, exist_ok=True)

    allres, port = {}, args.port0
    for target, conds in CONDITIONS.items():
        if args.only and args.only != target:
            continue
        for cond in conds:
            if args.cond and args.cond != cond["name"]:
                continue
            key = "%s/%s" % (target, cond["name"])
            print("== %s" % key, flush=True)
            run = Run(target, cond, args, port)
            port += 1
            try:
                run.prepare()
                run.setup()
                allres[key] = run.run_all()
            except Exception as e:  # keep going, record the failure
                import traceback; traceback.print_exc()
                allres[key] = {"ERROR": ("ERROR", str(e)[:1500])}
            finally:
                run.stop()
            for k, v in allres[key].items():
                print("  %-3s %-6s %s" % (k, v[0], v[1]), flush=True)

    json.dump(allres, open(args.out + ".json", "w"), indent=2)
    names = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "X1", "X2"]
    lines = ["| Condition | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for key, r in allres.items():
        lines.append("| %s | " % key + " | ".join(r.get(n, ("-",))[0] for n in names) + " |")
    lines.append("")
    lines.append("Harness self-check (expected flips):")
    for (t, c), exp in EXPECT.items():
        key = "%s/%s" % (t, c)
        if key in allres:
            bad = {d: (allres[key].get(d, ("-",))[0], s) for d, s in exp.items() if allres[key].get(d, ("-",))[0] != s}
            lines.append("- %s: %s" % (key, "OK" if not bad else "MISMATCH (got, expected) %s" % bad))
    lines.append("")
    for key, r in allres.items():
        lines.append("### " + key)
        for n in names + ["ERROR"]:
            if n in r:
                lines.append("- %s %s: %s" % (n, r[n][0], r[n][1]))
        lines.append("")
    open(args.out + ".md", "w").write("\n".join(lines))
    print("\n".join(lines[:len(allres) + 8]))


if __name__ == "__main__":
    main()
