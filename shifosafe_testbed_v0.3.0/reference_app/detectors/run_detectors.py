#!/usr/bin/env python3
"""Detectors D1-D8 against a running instance (reference app or any compatible target).

Usage: python3 run_detectors.py http://127.0.0.1:8000 [--password PW]
Prints one line per detector. A detector fires (FAIL) when the weakness is present.
Request sequences follow DETECTORS.md; the logic is the one used in fi_run.py of the v0.2.0 package.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request

PW = "Fi-Test-Pass-2026!"
BAD_PW = "Notogri-Parol-1"
DETECTORS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"]


class Target:
    def __init__(self, base, pw):
        self.base, self.pw = base.rstrip("/"), pw

    def req(self, method, path, token=None, body=None, accept="application/json"):
        data = json.dumps(body).encode() if body is not None else None
        h = {"Accept": accept}
        if data is not None:
            h["Content-Type"] = "application/json"
        if token:
            h["Authorization"] = "Bearer " + token
        r = urllib.request.Request(self.base + path, data=data, headers=h, method=method)
        try:
            resp = urllib.request.urlopen(r, timeout=30)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception as e:
            return 0, {}, str(e)
        st = getattr(resp, "status", None) or resp.code
        return st, {k.lower(): v for k, v in resp.headers.items()}, resp.read().decode("utf-8", "replace")

    def login(self, user, pw=None):
        st, _, tx = self.req("POST", "/api/auth/login/", body={"username": user, "password": pw or self.pw})
        d = js(tx) or {}
        return st, d.get("access"), d.get("refresh")


def js(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def items(obj):
    if isinstance(obj, dict) and "results" in obj:
        return obj["results"]
    return obj if isinstance(obj, list) else []


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), file=sys.stderr, flush=True)


def run_detectors(t, wait=62):
    """Returns {Dn: (fired, evidence, valid)}."""
    res = {}
    s1, a1, r1 = t.login("patient01")
    s2, a2, r2 = t.login("patient02")
    if not (a1 and a2):
        raise RuntimeError("cannot log in with the test accounts (%s, %s)" % (s1, s2))

    # D4: IDOR
    _, _, tx = t.req("GET", "/api/records/medical-records/", a2)
    recs2 = [x.get("id") for x in items(js(tx))]
    _, _, tx = t.req("GET", "/api/records/medical-records/", a1)
    recs1 = [x.get("id") for x in items(js(tx))]
    st = t.req("GET", "/api/records/medical-records/%s/" % recs2[0], a1)[0] if recs2 else None
    overlap = set(recs1) & set(recs2)
    res["D4"] = (st == 200 or bool(overlap), "foreign record GET=%s, list overlap=%d" % (st, len(overlap)), bool(recs2))

    # D5: privilege escalation
    st = t.req("GET", "/api/auth/users/", a1)[0]
    res["D5"] = (st == 200, "patient GET /api/auth/users/ = %s" % st, True)

    # D7: security headers
    need = ["x-content-type-options", "x-frame-options", "content-security-policy"]
    h_api = t.req("GET", "/api/auth/me/", a1)[1]
    h_root = t.req("GET", "/", accept="text/html")[1]
    miss = sorted({x for x in need if x not in h_api} | {x for x in need if x not in h_root})
    res["D7"] = (bool(miss), "missing: %s" % (",".join(miss) or "none"), True)

    # D8: debug page
    leak, sts = False, []
    for acc in ("text/html", "application/json"):
        st, _, tx = t.req("GET", "/api/records/no-such-endpoint/", a1, accept=acc)
        sts.append(st)
        if re.search(r"DEBUG = True|Using the URLconf|Traceback", tx):
            leak = True
    res["D8"] = (leak, "404 statuses=%s, debug trace=%s" % (sts, leak), True)

    # D6: account enumeration through password reset
    sa, _, ta = t.req("POST", "/api/auth/password-reset/", body={"email": "patient01@example.com"})
    sb, _, tb = t.req("POST", "/api/auth/password-reset/", body={"email": "no.such.person@example.com"})
    res["D6"] = ((sa, ta) != (sb, tb), "existing=%s, unknown=%s" % (sa, sb), sa != 429 and sb != 429)

    # D1: refresh token after logout
    stl = t.req("POST", "/api/auth/logout/", a2, body={"refresh": r2})[0]
    str_ = t.req("POST", "/api/auth/login/refresh/", body={"refresh": r2})[0]
    res["D1"] = (str_ == 200, "logout=%s, refresh after logout=%s" % (stl, str_), True)

    # D2: throttling (non-existing user, 12 attempts)
    codes = [t.req("POST", "/api/auth/login/", body={"username": "fi_no_such_user", "password": BAD_PW})[0]
             for _ in range(12)]
    res["D2"] = (429 not in codes, "12 attempts, statuses=%s" % sorted(set(codes)), True)

    # D3: lockout (5 wrong attempts after the throttle window has cleared, then the correct password)
    log("waiting %d s for the throttle window (D3)" % wait)
    time.sleep(wait)
    codes = [t.req("POST", "/api/auth/login/", body={"username": "patient20", "password": BAD_PW})[0]
             for _ in range(5)]
    log("waiting %d s again (D3)" % wait)
    time.sleep(wait)
    st = t.login("patient20")[0]
    res["D3"] = (st == 200, "5 wrong=%s, then correct password=%s" % (codes, st), 429 not in codes)
    return res


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    pw = sys.argv[sys.argv.index("--password") + 1] if "--password" in sys.argv else PW
    out = run_detectors(Target(base, pw))
    for k in DETECTORS:
        f, ev, ok = out[k]
        print("%s: %s | %s%s" % (k, "FIRES" if f else "silent", ev, "" if ok else "  [INVALID: precondition failed]"))
    print("JSON " + json.dumps({k: list(v) for k, v in out.items()}))
