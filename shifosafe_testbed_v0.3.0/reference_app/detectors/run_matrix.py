#!/usr/bin/env python3
"""Start the reference app once per configuration (BASE, F1..F8), run D1-D8, print the matrix.

Runs the nine configurations in parallel (ports 8100+), each with its own throw-away SQLite file.
Usage:  python3 detectors/run_matrix.py [BASE F1 F4 ...]      (from the reference_app folder)
Takes about 2.5 minutes in total (two 62-second waits for D3).
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_detectors import DETECTORS, Target, run_detectors  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL = ["BASE", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
NAMES = {"BASE": "healthy", "F1": "logout does not revoke", "F2": "throttling off", "F3": "lockout off",
         "F4": "IDOR", "F5": "patient reaches admin endpoint", "F6": "reset reveals account",
         "F7": "headers removed", "F8": "debug on"}
EXPECTED = {"BASE": set(), "F1": {"D1"}, "F2": {"D2"}, "F3": {"D3"}, "F4": {"D4"},
            "F5": {"D5"}, "F6": {"D6"}, "F7": {"D7"}, "F8": {"D8"}}


def run_one(cfg, port, tmp, results):
    env = dict(os.environ, REF_DB=os.path.join(tmp, cfg + ".sqlite3"),
               REF_FAULT="" if cfg == "BASE" else cfg, DJANGO_SETTINGS_MODULE="refapp.settings")
    py = sys.executable
    for cmd in ([py, "manage.py", "migrate", "--noinput"], [py, "manage.py", "seed_testdata"]):
        subprocess.run(cmd, cwd=HERE, env=env, check=True, capture_output=True)
    srv = subprocess.Popen([py, "manage.py", "runserver", "--noreload", "127.0.0.1:%d" % port],
                           cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        t = Target("http://127.0.0.1:%d" % port, "Fi-Test-Pass-2026!")
        for _ in range(60):
            if t.req("GET", "/api/auth/me/")[0] == 401:
                break
            time.sleep(1)
        results[cfg] = run_detectors(t)
    except Exception as e:  # keep the other configurations running
        results[cfg] = e
    finally:
        srv.terminate()


def main():
    cfgs = [c.upper() for c in sys.argv[1:]] or ALL
    results, threads = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        for i, c in enumerate(cfgs):
            th = threading.Thread(target=run_one, args=(c, 8100 + i, tmp, results))
            th.start(); threads.append(th)
        for th in threads:
            th.join()
    print("| Configuration | " + " | ".join(DETECTORS) + " | as expected |")
    print("|---|" + "---|" * (len(DETECTORS) + 1))
    ok_all = True
    for c in cfgs:
        r = results[c]
        if isinstance(r, Exception):
            print("| %s | ERROR: %s |" % (c, r)); ok_all = False; continue
        fired = {k for k in DETECTORS if r[k][0]}
        valid = all(r[k][2] for k in DETECTORS)
        ok = fired == EXPECTED[c] and valid
        ok_all &= ok
        print("| %s %s | %s | %s |" % (c, NAMES[c], " | ".join("T" if k in fired else "." for k in DETECTORS),
                                       "yes" if ok else "NO"))
    print("\nEvidence:")
    for c in cfgs:
        r = results[c]
        if not isinstance(r, Exception):
            for k in DETECTORS:
                if r[k][0] or c == "BASE":
                    print("  %-4s %s: %s" % (c, k, r[k][1]))
    with open(os.path.join(HERE, "matrix_result.json"), "w") as f:
        json.dump({c: ({k: list(v) for k, v in results[c].items()} if not isinstance(results[c], Exception)
                       else str(results[c])) for c in cfgs}, f, indent=1)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
