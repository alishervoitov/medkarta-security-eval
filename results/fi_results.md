# MedKarta: fault-injection experiment results (run of 2026-10-19)

## Table 1. Detection per injected fault

| ID | Injected fault | OWASP | State-aware test | Evidence | New ZAP alerts |
|---|---|---|---|---|---|
| F1 | Logout does not revoke the token | A07 | D1 detected | refresh after logout = 200 | none |
| F2 | Login throttling disabled | A07 | D2 detected | 12 attempts all 401, no 429 | none |
| F3 | Account lockout ineffective | A07 | D3 detected | correct password after 5 failures = 200 | none |
| F4 | IDOR: other patient's record readable | A01 | D4 detected | foreign record GET = 200, list overlap = 4 | none |
| F5 | Patient reaches admin endpoint | A01 | D5 detected | patient GET /auth/users/ = 200 | none |
| F6 | Password reset reveals account existence | A07 | D6 detected | existing = 200, unknown = 404 | none |
| F7 | Security headers removed | A02 | D7 detected | CSP, X-Content-Type-Options, X-Frame-Options missing | 4 alerts |
| F8 | Debug mode enabled | A02 | D8 detected | debug trace on 404 page | none |

## Table 2. Detector x configuration matrix (T = triggered, . = silent)

| Config | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 |
|---|---|---|---|---|---|---|---|---|
| BASE | . | . | . | . | . | . | . | . |
| F1 | T | . | . | . | . | . | . | . |
| F2 | . | T | . | . | . | . | . | . |
| F3 | . | . | T | . | . | . | . | . |
| F4 | . | . | . | T | . | . | . | . |
| F5 | . | . | . | . | T | . | . | . |
| F6 | . | . | . | . | . | T | . | . |
| F7 | . | . | . | . | . | . | T | . |
| F8 | . | . | . | . | . | . | . | T |

Summary: state-aware tests detected 8/8 faults; false positives on the fault-free
baseline: 0; ZAP baseline (passive, unauthenticated) raised new alerts for 1/8 faults (F7).
