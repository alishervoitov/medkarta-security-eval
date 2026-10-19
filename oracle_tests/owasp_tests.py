#!/usr/bin/env python3
"""MedKarta: OWASP Top 10 bo'yicha avtomatik xavfsizlik testlari.

Faqat o'z (demo) serveringizda ishga tushiring. Faqat standart kutubxona kerak.
Parollar muhit o'zgaruvchisidan yoki getpass orqali olinadi, ekranga/faylga yozilmaydi.

Ishga tushirish (serverda):
    python3 ~/owasp_tests.py
Boshqa manzil uchun:
    BASE=http://127.0.0.1 HOST=your.domain python3 ~/owasp_tests.py
"""
import base64
import getpass
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1").rstrip("/")
HOST = os.environ.get("HOST", "localhost")
API = "/api"
REPORT = os.environ.get("REPORT", "owasp_test_report.md")

RESULTS = []  # (id, owasp, test, kutilgan, haqiqiy, natija)


def req(method, path, token=None, body=None, extra=None, retry429=True):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Host": HOST, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    if extra:
        headers.update(extra)
    for attempt in range(4):
        r = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(r, timeout=30)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception as e:  # tarmoq xatosi
            return 0, {}, str(e)
        status = resp.status if hasattr(resp, "status") else resp.code
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        text = resp.read().decode("utf-8", "replace")
        if status == 429 and retry429 and attempt < 3:
            print("   ... so'rovlar limiti (429): 62 soniya kutilmoqda", flush=True)
            time.sleep(62)
            continue
        return status, hdrs, text
    return status, hdrs, text


def js(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def items(obj):
    if isinstance(obj, dict) and "results" in obj:
        return obj["results"]
    return obj if isinstance(obj, list) else []


def record(tid, owasp, test, expected, actual, verdict):
    RESULTS.append((tid, owasp, test, expected, str(actual), verdict))
    print(f"[{verdict:^6}] {tid:<5} {test} -> {actual}", flush=True)


def blocked(status):
    return status in (401, 403, 404)


def get_pw(env, label):
    return os.environ.get(env) or getpass.getpass(f"{label} paroli: ")


def login(username, password):
    st, _, tx = req("POST", f"{API}/auth/login/", body={"username": username, "password": password})
    d = js(tx) or {}
    return st, d.get("access"), d.get("refresh")


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def b64u_dec(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def main():
    print(f"Manzil: {BASE} (Host: {HOST})\n")
    pw = {
        "doctor1": get_pw("DOC1_PW", "doctor1"),
        "doctor2": get_pw("DOC2_PW", "doctor2"),
        "patient01": get_pw("PAT1_PW", "patient01"),
        "patient02": get_pw("PAT2_PW", "patient02"),
        "patient20": get_pw("PAT20_PW", "patient20 (brute-force qurboni)"),
    }
    print()

    # ---------- Tayyorgarlik ----------
    tok, ref = {}, {}
    for u in ("patient01", "patient02", "doctor1", "doctor2"):
        st, a, r = login(u, pw[u])
        if not a:
            print(f"XATO: {u} bilan kirib bo'lmadi (status {st}). Parolni tekshiring.")
            sys.exit(1)
        tok[u], ref[u] = a, r

    _, _, tx = req("GET", f"{API}/records/patients/me/", tok["patient01"])
    p1 = (js(tx) or {}).get("id")
    _, _, tx = req("GET", f"{API}/records/patients/me/", tok["patient02"])
    p2 = (js(tx) or {}).get("id")
    _, _, tx = req("GET", f"{API}/records/medical-records/", tok["patient02"])
    rec2 = [x.get("id") for x in items(js(tx))]
    _, _, tx = req("GET", f"{API}/records/medical-records/", tok["patient01"])
    rec1 = [x.get("id") for x in items(js(tx))]
    _, _, tx = req("GET", f"{API}/records/prescriptions/", tok["patient02"])
    rx2 = [x.get("id") for x in items(js(tx))]
    print(f"Tayyorgarlik: patient01 id={p1}, patient02 id={p2}, "
          f"p2 yozuvlari={len(rec2)}, p2 retseptlari={len(rx2)}\n")

    # ---------- A01: Broken Access Control ----------
    A = "A01 Buzilgan kirish nazorati"
    if p2:
        st, _, _ = req("GET", f"{API}/records/patients/{p2}/", tok["patient01"])
        record("T01", A, "IDOR: bemor boshqa bemor profilini ko'radi", "403/404", st,
               "PASS" if blocked(st) else "FAIL")
        st, _, _ = req("GET", f"{API}/records/patients/{p2}/history-pdf/", tok["patient01"])
        record("T02", A, "IDOR: bemor boshqa bemor PDF tarixini yuklaydi", "403/404", st,
               "PASS" if blocked(st) else "FAIL")
    if rec2:
        st, _, _ = req("GET", f"{API}/records/medical-records/{rec2[0]}/", tok["patient01"])
        record("T03", A, "IDOR: bemor boshqa bemor tibbiy yozuvini oladi", "403/404", st,
               "PASS" if blocked(st) else "FAIL")
        st, _, _ = req("PATCH", f"{API}/records/medical-records/{rec2[0]}/", tok["patient01"],
                       body={"title": "hacked"})
        record("T04", A, "IDOR: bemor boshqa bemor yozuvini o'zgartiradi", "403/404/405", st,
               "PASS" if st in (403, 404, 405) else "FAIL")
        st, _, _ = req("DELETE", f"{API}/records/medical-records/{rec2[0]}/", tok["patient01"])
        record("T05", A, "IDOR: bemor boshqa bemor yozuvini o'chiradi", "403/404/405", st,
               "PASS" if st in (403, 404, 405) else "FAIL")
    if rx2:
        st, _, _ = req("GET", f"{API}/records/prescriptions/{rx2[0]}/", tok["patient01"])
        record("T06", A, "IDOR: bemor boshqa bemor retseptini oladi", "403/404", st,
               "PASS" if blocked(st) else "FAIL")
    overlap = set(rec1) & set(rec2)
    record("T07", A, "Ro'yxat izolyatsiyasi: bemor ro'yxatida boshqa bemor yozuvlari yo'q",
           "kesishma yo'q", f"kesishma={len(overlap)}", "PASS" if not overlap else "FAIL")

    st, _, tx = req("GET", f"{API}/records/patients/", tok["patient01"])
    ids = [x.get("id") for x in items(js(tx))]
    ok = st in (403, 404) or (st == 200 and set(ids) <= {p1})
    record("T08", A, "Bemor barcha bemorlar ro'yxatini ko'radi", "403 yoki faqat o'zi",
           f"{st}, ro'yxat={len(ids)}", "PASS" if ok else "FAIL")
    for tid, path in (("T09", "/auth/users/"), ("T10", "/records/audit-logs/"),
                      ("T11", "/records/export-anonymized/")):
        st, _, _ = req("GET", API + path, tok["patient01"])
        record(tid, A, f"Rolni oshirish: bemor {path} ga kiradi", "403", st,
               "PASS" if st == 403 else "FAIL")
    for tid, path in (("T12", "/auth/users/"), ("T13", "/records/audit-logs/")):
        st, _, _ = req("GET", API + path, tok["doctor1"])
        record(tid, A, f"Rolni oshirish: shifokor (admin emas) {path} ga kiradi", "403", st,
               "PASS" if st == 403 else "FAIL")
    st, _, _ = req("POST", f"{API}/auth/users/", tok["patient01"],
                   body={"username": "evil_admin", "password": "Xx12345678!!", "role": "admin"})
    record("T14", A, "Rolni oshirish: bemor admin foydalanuvchi yaratadi", "403", st,
           "PASS" if st == 403 else "FAIL")
    if p2:
        st, _, _ = req("GET", f"{API}/records/patients/{p2}/", tok["doctor1"])
        record("T15", A, "Shifokor boshqa shifokorning bemoriga kiradi (siyosatga bog'liq)",
               "ma'lumot", st, "INFO")
    for i, p in enumerate(("/auth/me/", "/records/patients/", "/records/medical-records/",
                           "/records/prescriptions/", "/records/audit-logs/",
                           f"/records/patients/{p2 or 1}/history-pdf/"), 1):
        st, _, _ = req("GET", API + p)
        record(f"T16.{i}", A, f"Tokensiz kirish: {p}", "401", st, "PASS" if st == 401 else "FAIL")

    # ---------- A05: Injection ----------
    A = "A05 Inyeksiya"
    sqli = ["' OR '1'='1", "admin'--", "\" OR 1=1 --", "'; DROP TABLE users_user;--"]
    bad = False
    codes = []
    for payload in sqli:
        st, _, tx = req("POST", f"{API}/auth/login/", body={"username": payload, "password": payload})
        codes.append(st)
        if st == 200 or st >= 500 or re.search(r"psycopg|syntax error|Traceback", tx, re.I):
            bad = True
    record("T20", A, "SQL inyeksiya: login maydoni (4 ta yuklama)", "401/400, 500 va DB xatosi yo'q",
           codes, "FAIL" if bad else "PASS")
    for tid, qs in (("T21", "search=' OR 1=1--"), ("T22", "ordering=id;DROP TABLE x"),
                    ("T23", "search=%27%20UNION%20SELECT%20NULL--")):
        enc = urllib.parse.quote(qs, safe="=&%")
        st, _, tx = req("GET", f"{API}/records/patients/?{enc}", tok["doctor1"])
        bad = st >= 500 or bool(re.search(r"psycopg|syntax error|Traceback|OperationalError", tx, re.I))
        record(tid, A, f"SQL inyeksiya: so'rov parametri ({qs[:30]})", "200/400, 500 yo'q", st,
               "SKIP" if st == 0 else ("FAIL" if bad else "PASS"))
    st, _, _ = req("GET", f"{API}/records/patients/1%20OR%201=1/", tok["doctor1"])
    record("T24", A, "SQL inyeksiya: URL ichidagi pk", "404", st, "PASS" if st == 404 else "FAIL")

    xss = "<script>alert('xss')</script>"
    if p1:
        st, h, tx = req("POST", f"{API}/records/medical-records/", tok["doctor1"], body={
            "patient": p1, "record_type": "visit", "title": xss,
            "diagnosis": "<img src=x onerror=alert(1)>", "treatment": "test",
            "visit_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        if st in (200, 201):
            ct = h.get("content-type", "")
            nos = h.get("x-content-type-options", "").lower() == "nosniff"
            ok = "application/json" in ct and nos
            record("T25", A, "Saqlangan XSS: yuklama JSON sifatida qaytadi, brauzer ijro etmaydi",
                   "application/json + nosniff", f"{st}, {ct}, nosniff={nos}", "PASS" if ok else "FAIL")
        else:
            record("T25", A, "Saqlangan XSS yozuvi yaratish", "201", f"{st}: {tx[:80]}", "SKIP")
    st, _, tx = req("POST", f"{API}/auth/register/", body={
        "username": xss, "password": "Xx12345678!!", "email": "x@example.com"})
    record("T26", A, "XSS: ro'yxatdan o'tishda <script> username", "400 (rad etiladi)", st,
           "PASS" if st == 400 else "FAIL")

    # ---------- A07: Authentication Failures ----------
    A = "A07 Autentifikatsiya xatolari"
    access = tok["patient01"]
    h_, p_, s_ = access.split(".")
    # imzoni buzish
    sig = list(s_)
    sig[2] = "A" if sig[2] != "A" else "B"
    forged = ".".join([h_, p_, "".join(sig)])
    st, _, _ = req("GET", f"{API}/auth/me/", forged)
    record("T30", A, "JWT: imzosi buzilgan token", "401", st, "PASS" if st == 401 else "FAIL")
    # alg=none
    nh = b64u(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    st, _, _ = req("GET", f"{API}/auth/me/", f"{nh}.{p_}.")
    record("T31", A, "JWT: alg=none hujumi", "401", st, "PASS" if st == 401 else "FAIL")
    # payloadni o'zgartirish (boshqa user_id), eski imzo bilan
    try:
        pl = json.loads(b64u_dec(p_))
        pl["user_id"] = 1
        st, _, _ = req("GET", f"{API}/auth/me/", f"{h_}.{b64u(json.dumps(pl).encode())}.{s_}")
        record("T32", A, "JWT: payload (user_id) o'zgartirilgan, eski imzo", "401", st,
               "PASS" if st == 401 else "FAIL")
    except Exception as e:
        record("T32", A, "JWT payload o'zgartirish", "401", f"xato: {e}", "SKIP")
    st, _, _ = req("GET", f"{API}/auth/me/", ref["patient01"])
    record("T33", A, "JWT: refresh token access o'rniga ishlatiladi", "401", st,
           "PASS" if st == 401 else "FAIL")
    st, _, _ = req("GET", f"{API}/auth/me/", "abc.def.ghi")
    record("T34", A, "JWT: noto'g'ri formatdagi token", "401", st, "PASS" if st == 401 else "FAIL")

    # logout -> refresh qora ro'yxat
    st, _, tx = req("POST", f"{API}/auth/logout/", tok["patient02"], body={"refresh": ref["patient02"]})
    if st in (200, 204, 205):
        st2, _, _ = req("POST", f"{API}/auth/login/refresh/", body={"refresh": ref["patient02"]})
        record("T35", A, "Logoutdan keyin refresh token qora ro'yxatda", "401", st2,
               "PASS" if st2 == 401 else "FAIL")
    else:
        record("T35", A, "Logout (token qora ro'yxati)", "200/205", f"{st}: {tx[:60]}", "SKIP")

    # parol tiklash: foydalanuvchini aniqlash (enumeration)
    st_a, _, tx_a = req("POST", f"{API}/auth/password-reset/", body={"email": "patient01@example.com"})
    st_b, _, tx_b = req("POST", f"{API}/auth/password-reset/", body={"email": "yoq.odam@example.com"})
    same = (st_a == st_b) and (tx_a == tx_b)
    record("T36", A, "Parol tiklash: mavjud va mavjud bo'lmagan email javobi bir xil",
           "bir xil javob", f"{st_a}/{st_b}, bir xil={same}", "PASS" if same else "FAIL")

    # brute-force (patient20)
    codes = []
    for _ in range(7):
        st, _, tx = req("POST", f"{API}/auth/login/",
                        body={"username": "patient20", "password": "NotoGri-Parol-1"}, retry429=False)
        codes.append(st)
    throttled = 429 in codes
    record("T37", A, "Brute-force: 7 ta noto'g'ri parol ketma-ket", "429 limit yoki blok",
           codes, "PASS" if throttled or codes[-1] in (403, 423) else "FAIL")
    print("   ... 62 soniya kutilmoqda (limit tugashi uchun), keyin TO'G'RI parol bilan urinib ko'riladi",
          flush=True)
    time.sleep(62)
    st, _, tx = req("POST", f"{API}/auth/login/",
                    body={"username": "patient20", "password": pw["patient20"]}, retry429=False)
    record("T38", A, "Akkaunt bloklanishi: limitdan keyin to'g'ri parol ham rad etiladi",
           "401/403/423 (blok)", st, "PASS" if st != 200 else "FAIL")

    # ---------- A02 / A09: Konfiguratsiya ----------
    A = "A02 Noto'g'ri sozlama"
    st, h, tx = req("GET", f"{API}/records/yoq-endpoint/", tok["doctor1"])
    leak = bool(re.search(r"Traceback|DEBUG = True|settings\.py|Django Version", tx))
    record("T40", A, "Xato sahifasida debug/stack trace yo'q", "404, ma'lumot sizmaydi", st,
           "FAIL" if leak else "PASS")
    st, h, _ = req("GET", f"{API}/auth/me/", tok["patient01"], extra={"Origin": "https://evil.example"})
    acao = h.get("access-control-allow-origin", "")
    record("T41", A, "CORS: begona origin ruxsat etilmaydi", "ACAO yo'q yoki * emas",
           acao or "yo'q", "PASS" if acao in ("", ) else "FAIL")
    st, h, _ = req("GET", f"{API}/auth/me/", tok["patient01"])
    need = ["x-content-type-options", "x-frame-options", "content-security-policy"]
    miss = [x for x in need if x not in h]
    record("T42", A, "API javobida xavfsizlik sarlavhalari bor", "hammasi bor",
           "yetishmaydi: " + ",".join(miss) if miss else "hammasi bor", "FAIL" if miss else "PASS")
    record("T43", A, "Server sarlavhasi versiyani oshkor qilmaydi", "versiyasiz",
           h.get("server", "yo'q"), "PASS" if not re.search(r"\d", h.get("server", "")) else "FAIL")

    # ---------- Hisobot ----------
    npass = sum(1 for r in RESULTS if r[5] == "PASS")
    nfail = sum(1 for r in RESULTS if r[5] == "FAIL")
    nskip = sum(1 for r in RESULTS if r[5] in ("SKIP", "INFO"))
    lines = ["# MedKarta: OWASP Top 10 avtomatik test hisoboti", "",
             f"Sana: {time.strftime('%Y-%m-%d %H:%M')} | Maqsad: {BASE}", "",
             f"**Jami: {len(RESULTS)} | O'tdi: {npass} | O'tmadi: {nfail} | Ma'lumot/o'tkazib yuborilgan: {nskip}**", "",
             "| № | OWASP | Test | Kutilgan | Haqiqiy | Natija |", "|---|---|---|---|---|---|"]
    for r in RESULTS:
        lines.append("| " + " | ".join(x.replace("|", "/") for x in r) + " |")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nJami {len(RESULTS)}: o'tdi {npass}, o'tmadi {nfail}, ma'lumot/skip {nskip}")
    print(f"Hisobot: {os.path.abspath(REPORT)}")
    print("\nESLATMA: patient20 15 daqiqaga bloklangan. Darhol ochish uchun:")
    print("docker compose -f docker-compose.prod.yml exec backend python manage.py shell -c "
          "\"from users.models import User; User.objects.filter(username='patient20')"
          ".update(failed_login_attempts=0, locked_until=None)\"")


if __name__ == "__main__":
    main()
