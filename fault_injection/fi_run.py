#!/usr/bin/env python3
"""MedKarta: nazoratli nuqson kiritish (fault injection) tajribasi.

Ishlayotgan demo serverga TEGMAYDI. Kodning nusxasini ~/fi_experiment ga ko'chiradi,
alohida docker loyihasi (fi) va alohida port (127.0.0.1:8081) da ishga tushiradi.
Har bir konfiguratsiyada: nuqson kiritiladi -> qayta yig'iladi -> detektorlar
(holatni kuzatuvchi testlar) va ZAP baseline ishga tushadi -> natija saqlanadi.

Ishga tushirish:
    python3 ~/fi_run.py BASE --no-zap          # sinov: faqat baseline, ZAPsiz
    nohup python3 ~/fi_run.py > ~/fi_log.txt 2>&1 &    # to'liq tajriba
    python3 ~/fi_run.py F1 F4 --no-zap         # tanlangan nuqsonlar
    python3 ~/fi_run.py down                   # nusxa stekini to'xtatish va o'chirish
Natija: ~/fi_experiment/results/fi_results.md
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

SRC_B = os.environ.get("MEDKARTA_BACKEND", "/opt/medkarta/dissertatsiya")
SRC_F = os.environ.get("MEDKARTA_FRONTEND", "/opt/medkarta/frontend")
EXP = os.path.expanduser("~/fi_experiment")
CLEAN_B = EXP + "/clean_backend"
CLEAN_F = EXP + "/clean_frontend"
WORK_B = EXP + "/dissertatsiya"
WORK_F = EXP + "/frontend"
OUT = EXP + "/results"
PROJ = "fi"
PORT = 8081
BASE_URL = "http://127.0.0.1:%d" % PORT
HOST = "medkarta.example"  # value of the Host header sent to the throw-away copy
PW = "Fi-Test-Pass-2026!"  # faqat shu vaqtinchalik, 127.0.0.1 dagi nusxa uchun
BAD_PW = "Notogri-Parol-1"

ALL = ["BASE", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
META = {
    "BASE": ("Nuqsonsiz (nazorat)", "-", "-"),
    "F1": ("Logout tokenni bekor qilmaydi", "A07", "D1"),
    "F2": ("Login throttling o'chirilgan", "A07", "D2"),
    "F3": ("Akkaunt bloklash ishlamaydi", "A07", "D3"),
    "F4": ("IDOR: boshqa bemor yozuvi ochiq", "A01", "D4"),
    "F5": ("Bemor admin endpointiga kiradi", "A01", "D5"),
    "F6": ("Parol tiklashda foydalanuvchi aniqlanadi", "A07", "D6"),
    "F7": ("Xavfsizlik sarlavhalari olib tashlangan", "A02", "D7"),
    "F8": ("Debug rejimi yoqilgan", "A02", "D8"),
}
DETECTORS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"]


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def sh(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str),
                       capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError("buyruq xatosi: %s\n%s\n%s" % (cmd, p.stdout[-1500:], p.stderr[-1500:]))
    return p


def dc(*args, check=True):
    return sh(["docker", "compose", "-p", PROJ, "-f", "docker-compose.fi.yml"] + list(args),
              cwd=WORK_B, check=check)


def copy_tree(src, dst, excludes):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    ex = " ".join("--exclude='%s'" % e for e in excludes)
    sh("tar -C '%s' %s -cf - . | tar -C '%s' -xf -" % (src, ex, dst))


B_EXCL = ["./.git", "./media", "./protected_media"]
F_EXCL = ["./.git", "./node_modules", "./dist"]


# ---------------------------------------------------------------- mutatsiyalar
def sub(path, pattern, repl, regex=False, count=1, flags=0):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    cnt = 0 if count is None else count
    if regex:
        s2, n = re.subn(pattern, repl, s, count=cnt, flags=flags)
    else:
        n = s.count(pattern)
        s2 = s.replace(pattern, repl, cnt if cnt else -1)
    if n == 0:
        raise RuntimeError("mutatsiya qo'llanmadi: %s :: %s" % (path, str(pattern)[:60]))
    with open(path, "w", encoding="utf-8") as f:
        f.write(s2)


def f1():
    sub(WORK_B + "/config/settings.py",
        r'^[ \t]*"rest_framework_simplejwt\.token_blacklist",[ \t]*\n', "",
        regex=True, flags=re.M)


def f2():
    sub(WORK_B + "/config/settings.py", '"login": "5/min"', '"login": "100000/min"')


def f3():
    sub(WORK_B + "/users/serializers.py",
        "user.failed_login_attempts += 1", "user.failed_login_attempts += 0")


def f4():
    sub(WORK_B + "/records/permissions.py",
        r'(class MedicalRecordObjectPermission.*?)return obj\.patient\.user_id == user\.id and request\.method in SAFE_METHODS',
        r'\1return request.method in SAFE_METHODS', regex=True, flags=re.S)
    sub(WORK_B + "/records/views.py",
        r'(class MedicalRecordListCreateView.*?)qs = qs\.filter\(patient__user=user\)',
        r'\1qs = qs', regex=True, flags=re.S)


def f5():
    sub(WORK_B + "/users/views.py", r'permission_classes = \[IsAdmin\]',
        'permission_classes = [permissions.IsAuthenticated]', regex=True, count=None)


def f6():
    sub(WORK_B + "/users/views.py",
        r'(email topilmadi: %s", email\)\n\s+)return generic_response',
        r'\1return Response({"detail": "Bunday email topilmadi."}, status=status.HTTP_404_NOT_FOUND)',
        regex=True)


def f7():
    sub(WORK_F + "/nginx.conf",
        r'add_header\s+\S+\s+(?:"[^"]*"|\'[^\']*\'|[^;"\']+)(?:\s+always)?\s*;',
        "", regex=True, count=None)


def f8():
    p = WORK_B + "/.env.docker"
    with open(p, encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if not l.strip().startswith("DEBUG=")]
    lines.append("DEBUG=True")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


FAULTS = {"F1": f1, "F2": f2, "F3": f3, "F4": f4, "F5": f5, "F6": f6, "F7": f7, "F8": f8}


# ---------------------------------------------------------------- HTTP
def req(method, path, token=None, body=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Host": HOST, "Accept": accept}
    if data is not None:
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = "Bearer " + token
    r = urllib.request.Request(BASE_URL + path, data=data, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=30)
    except urllib.error.HTTPError as e:
        resp = e
    except Exception as e:
        return 0, {}, str(e)
    st = getattr(resp, "status", None) or resp.code
    hd = {k.lower(): v for k, v in resp.headers.items()}
    return st, hd, resp.read().decode("utf-8", "replace")


def js(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def items(obj):
    if isinstance(obj, dict) and "results" in obj:
        return obj["results"]
    return obj if isinstance(obj, list) else []


def login(user, pw):
    st, _, tx = req("POST", "/api/auth/login/", body={"username": user, "password": pw})
    d = js(tx) or {}
    return st, d.get("access"), d.get("refresh")


# ---------------------------------------------------------------- detektorlar
def run_detectors():
    """Har bir detektor: (nuqson_topildimi, dalil, yaroqli). Nazoratda hammasi False bo'lishi kerak."""
    res = {}
    s1, a1, r1 = login("patient01", PW)
    s2, a2, r2 = login("patient02", PW)
    if not (a1 and a2):
        raise RuntimeError("test akkauntlari bilan kirib bo'lmadi (%s, %s)" % (s1, s2))

    # D4: IDOR (boshqa bemor yozuvi)
    _, _, tx = req("GET", "/api/records/medical-records/", a2)
    recs2 = [x.get("id") for x in items(js(tx))]
    _, _, tx = req("GET", "/api/records/medical-records/", a1)
    recs1 = [x.get("id") for x in items(js(tx))]
    if recs2:
        st, _, _ = req("GET", "/api/records/medical-records/%s/" % recs2[0], a1)
    else:
        st = None
    overlap = set(recs1) & set(recs2)
    res["D4"] = (st == 200 or bool(overlap),
                 "boshqa yozuv GET=%s, ro'yxat kesishmasi=%d" % (st, len(overlap)), bool(recs2))

    # D5: rolni oshirish (bemor foydalanuvchilar ro'yxatiga kiradi)
    st, _, _ = req("GET", "/api/auth/users/", a1)
    res["D5"] = (st == 200, "bemor GET /auth/users/ = %s" % st, True)

    # D7: xavfsizlik sarlavhalari
    need = ["x-content-type-options", "x-frame-options", "content-security-policy"]
    _, h_api, _ = req("GET", "/api/auth/me/", a1)
    _, h_root, _ = req("GET", "/", accept="text/html")
    miss = sorted(set([x for x in need if x not in h_api]) | set([x for x in need if x not in h_root]))
    res["D7"] = (bool(miss), "yetishmaydi: %s" % (",".join(miss) or "yo'q"), True)

    # D8: debug sahifasi
    leak = False
    sts = []
    for acc in ("text/html", "application/json"):
        st, _, tx = req("GET", "/api/records/yoq-endpoint/", a1, accept=acc)
        sts.append(st)
        if re.search(r"DEBUG = True|Using the URLconf|Traceback", tx):
            leak = True
    res["D8"] = (leak, "404 sahifa statuslari=%s, debug izi=%s" % (sts, leak), True)

    # D6: parol tiklashda foydalanuvchini aniqlash
    sa, _, ta = req("POST", "/api/auth/password-reset/", body={"email": "patient01@example.com"})
    sb, _, tb = req("POST", "/api/auth/password-reset/", body={"email": "yoq.odam@example.com"})
    res["D6"] = ((sa, ta) != (sb, tb), "mavjud=%s, mavjud emas=%s" % (sa, sb), sa != 429 and sb != 429)

    # D1: logoutdan keyin refresh token
    stl, _, _ = req("POST", "/api/auth/logout/", a2, body={"refresh": r2})
    str_, _, _ = req("POST", "/api/auth/login/refresh/", body={"refresh": r2})
    res["D1"] = (str_ == 200, "logout=%s, logoutdan keyingi refresh=%s" % (stl, str_), True)

    # D2: throttling (mavjud bo'lmagan foydalanuvchi, 12 ta urinish)
    codes = []
    for _ in range(12):
        st, _, _ = req("POST", "/api/auth/login/",
                       body={"username": "fi_no_such_user", "password": BAD_PW})
        codes.append(st)
    res["D2"] = (429 not in codes, "12 urinish statuslari=%s" % sorted(set(codes)), True)

    # D3: akkaunt bloklash (limit oynasi tozalangach 5 noto'g'ri, keyin to'g'ri parol)
    log("   limit oynasi tozalanishi uchun 62 soniya kutilmoqda (D3)")
    time.sleep(62)
    codes = []
    for _ in range(5):
        st, _, _ = req("POST", "/api/auth/login/", body={"username": "patient20", "password": BAD_PW})
        codes.append(st)
    log("   bloklanish tekshiruvi uchun yana 62 soniya kutilmoqda (D3)")
    time.sleep(62)
    st, _, _ = login("patient20", PW)
    res["D3"] = (st == 200, "5 noto'g'ri=%s, keyin to'g'ri parol=%s" % (codes, st), 429 not in codes)
    return res


# ---------------------------------------------------------------- ZAP
def zap_image():
    p = sh("docker images --format '{{.Repository}}:{{.Tag}}'", check=False)
    for l in p.stdout.split():
        if "zap" in l.lower() and "<none>" not in l:
            return l
    return "ghcr.io/zaproxy/zaproxy:stable"


def run_zap(cfg):
    d = OUT + "/zap"
    os.makedirs(d, exist_ok=True)
    os.chmod(d, 0o777)
    fn = "zap_%s.json" % cfg
    log("   ZAP baseline ishga tushdi (taxminan 2 daqiqa)")
    rep = ("-config replacer.full_list(0).description=host -config replacer.full_list(0).enabled=true "
           "-config replacer.full_list(0).matchtype=REQ_HEADER -config replacer.full_list(0).matchstr=Host "
           "-config replacer.full_list(0).regex=false -config replacer.full_list(0).replacement=%s" % HOST)
    zp = sh(["docker", "run", "--rm", "--network", "host", "-v", "%s:/zap/wrk:rw" % d, zap_image(),
             "zap-baseline.py", "-t", "http://127.0.0.1:%d" % PORT, "-J", fn, "-m", "1", "-I", "-z", rep],
            check=False)
    if not os.path.exists(d + "/" + fn):
        log("   ZAP chiqishi: " + (zp.stdout + zp.stderr)[-500:].replace("\n", " | "))
    alerts = set()
    try:
        with open(d + "/" + fn, encoding="utf-8") as f:
            data = json.load(f)
        for site in data.get("site", []):
            for a in site.get("alerts", []):
                alerts.add("%s|%s" % (a.get("pluginid"), a.get("alert") or a.get("name")))
    except Exception as e:
        log("   ZAP hisobotini o'qib bo'lmadi: %s" % e)
        return None
    return sorted(alerts)


# ---------------------------------------------------------------- stek
SEED = """
from django.utils import timezone
from users.models import User, Role
from records.models import MedicalRecord, Patient
PW = '__PW__'
doc = None
for u in ['doctor1', 'doctor2']:
    x, c = User.objects.get_or_create(username=u, defaults=dict(email=u + '@example.com', role=Role.DOCTOR, first_name=u, last_name='Test'))
    x.set_password(PW); x.failed_login_attempts = 0; x.locked_until = None; x.save()
    if u == 'doctor1':
        doc = x
for u in ['patient01', 'patient02', 'patient20']:
    x, c = User.objects.get_or_create(username=u, defaults=dict(email=u + '@example.com', role=Role.PATIENT, first_name=u, last_name='Test'))
    x.set_password(PW); x.failed_login_attempts = 0; x.locked_until = None; x.save()
    pat = Patient.objects.get(user=x)
    if u != 'patient20' and not MedicalRecord.objects.filter(patient=pat).exists():
        for i in range(2):
            MedicalRecord.objects.create(patient=pat, created_by=doc, record_type='visit', title='FI test %d' % i, diagnosis='Sog\\'lom', treatment='Tavsiyalar', visit_date=timezone.now())
print('SEED_OK')
"""


def wait_ready(tries=90):
    for _ in range(tries):
        st, _, _ = req("GET", "/api/auth/me/")
        if st == 401:
            return
        time.sleep(3)
    raise RuntimeError("stek 270 soniyada tayyor bo'lmadi (docker compose -p fi logs backend ni ko'ring)")


def run_config(cfg, zap):
    log("=== %s: %s" % (cfg, META[cfg][0]))
    copy_tree(CLEAN_B, WORK_B, [])
    copy_tree(CLEAN_F, WORK_F, [])
    with open(WORK_B + "/docker-compose.prod.yml", encoding="utf-8") as f:
        s = f.read()
    if '"80:80"' not in s:
        raise RuntimeError("compose faylida \"80:80\" topilmadi")
    with open(WORK_B + "/docker-compose.fi.yml", "w", encoding="utf-8") as f:
        f.write(s.replace('"80:80"', '"127.0.0.1:%d:80"' % PORT))
    if cfg != "BASE":
        FAULTS[cfg]()
        log("   nuqson kiritildi")
    log("   yig'ilmoqda va ishga tushirilmoqda (birinchi marta uzoq davom etishi mumkin)")
    dc("up", "-d", "--build", "db", "redis", "backend", "web")
    wait_ready()
    dc("restart", "web")
    wait_ready()
    p = dc("exec", "-T", "backend", "python", "manage.py", "shell", "-c", SEED.replace("__PW__", PW))
    if "SEED_OK" not in p.stdout:
        raise RuntimeError("test ma'lumotlarini yaratib bo'lmadi:\n" + p.stdout[-800:] + p.stderr[-800:])
    dc("exec", "-T", "redis", "redis-cli", "FLUSHALL")
    det = run_detectors()
    for k in DETECTORS:
        v = det[k]
        log("   %s: %s | %s%s" % (k, "TOPILDI" if v[0] else "topilmadi", v[1],
                                 "" if v[2] else "  [YAROQSIZ: shartlar buzildi]"))
    alerts = run_zap(cfg) if zap else None
    os.makedirs(OUT, exist_ok=True)
    with open("%s/%s.json" % (OUT, cfg), "w", encoding="utf-8") as f:
        json.dump({"cfg": cfg, "det": {k: list(v) for k, v in det.items()}, "zap": alerts}, f,
                  ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- hisobot
def load_results():
    r = {}
    for cfg in ALL:
        p = "%s/%s.json" % (OUT, cfg)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                r[cfg] = json.load(f)
    return r


def report():
    r = load_results()
    if not r:
        return
    base = r.get("BASE")
    base_zap = set(base["zap"]) if base and base.get("zap") is not None else None
    L = ["# MedKarta: nazoratli nuqson kiritish tajribasi natijalari", "",
         "Sana: %s" % time.strftime("%Y-%m-%d %H:%M"), ""]
    L += ["## 1-jadval. Nuqson bo'yicha topilish", "",
          "| № | Nuqson | Toifa | Holatga bog'liq test | Dalil | ZAP yangi ogohlantirishlari |",
          "|---|---|---|---|---|---|"]
    own_hits = 0
    own_total = 0
    zap_hits = 0
    zap_total = 0
    for cfg in ALL[1:]:
        if cfg not in r:
            continue
        name, cat, det = META[cfg]
        d = r[cfg]["det"][det]
        own_total += 1
        if d[0] and d[2]:
            own_hits += 1
        verdict = "TOPDI" if d[0] else "topmadi"
        if not d[2]:
            verdict += " (yaroqsiz)"
        z = r[cfg].get("zap")
        if z is None or base_zap is None:
            zt = "o'lchanmagan"
        else:
            new = sorted(set(z) - base_zap)
            zap_total += 1
            if new:
                zap_hits += 1
            zt = "; ".join(x.split("|", 1)[1] for x in new) if new else "yo'q"
        L.append("| %s | %s | %s | %s %s | %s | %s |" % (cfg, name, cat, det, verdict, d[1], zt))
    L += ["", "## 2-jadval. Detektorlar matritsasi (qator: konfiguratsiya, ustun: detektor)", "",
          "| Konfiguratsiya | " + " | ".join(DETECTORS) + " |",
          "|---|" + "---|" * len(DETECTORS)]
    for cfg in ALL:
        if cfg not in r:
            continue
        cells = ["TOPILDI" if r[cfg]["det"][k][0] else "." for k in DETECTORS]
        L.append("| %s | %s |" % (cfg, " | ".join(cells)))
    fp = 0
    if base:
        fp = sum(1 for k in DETECTORS if base["det"][k][0])
    L += ["", "## Xulosa", "",
          "- Holatga bog'liq testlar: %d/%d nuqsonni topdi." % (own_hits, own_total),
          "- Nazoratda (nuqsonsiz) yolg'on signallar: %s." % (fp if base else "o'lchanmagan"),
          "- ZAP baseline nazoratga nisbatan yangi ogohlantirish bergan: %s." %
          ("%d/%d (mosligini qo'lda tekshirish kerak)" % (zap_hits, zap_total) if zap_total else "o'lchanmagan"),
          ""]
    with open(OUT + "/fi_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    log("Hisobot: %s/fi_results.md" % OUT)
    print("\n" + "\n".join(L), flush=True)


def prepare_clean():
    for p in (SRC_B, SRC_F):
        if not os.path.isdir(p):
            raise RuntimeError("papka topilmadi: " + p)
    os.makedirs(EXP, exist_ok=True)
    if not os.path.isdir(CLEAN_B):
        log("toza nusxa olinmoqda (backend)")
        copy_tree(SRC_B, CLEAN_B, B_EXCL)
    if not os.path.isdir(CLEAN_F):
        log("toza nusxa olinmoqda (frontend)")
        copy_tree(SRC_F, CLEAN_F, F_EXCL)


def main():
    args = sys.argv[1:]
    if args and args[0] == "down":
        if os.path.isdir(WORK_B):
            dc("down", "-v", check=False)
        log("nusxa stegi o'chirildi")
        return
    zap = "--no-zap" not in args
    cfgs = [a for a in args if not a.startswith("--")] or list(ALL)
    for c in cfgs:
        if c not in META:
            raise SystemExit("noma'lum konfiguratsiya: %s (mumkin: %s)" % (c, " ".join(ALL)))
    if "BASE" not in cfgs and not os.path.exists(OUT + "/BASE.json"):
        cfgs.insert(0, "BASE")
    prepare_clean()
    try:
        for c in cfgs:
            run_config(c, zap)
    finally:
        if "--keep" not in args and os.path.isdir(WORK_B):
            dc("down", "-v", check=False)
            log("nusxa stegi to'xtatildi")
    report()


if __name__ == "__main__":
    main()
