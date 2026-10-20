# Pre-registered fault list: wger-project/wger (written before any wger fault run)

Date: 2026-10-20. Target commit: shallow clone of master as of 2026-10-20 (last upstream commit 2026-10-19).
Baseline expectation: every control PASSES on the unmodified code (D7 may fail if the framework omits a header;
that outcome will be reported as found, not adjusted).

| ID | Control (OWASP) | Injection | Expected detector flip |
|----|-----------------|-----------|------------------------|
| W-F2 | Brute-force protection (A07) | environment AXES_ENABLED=0 (django-axes off) | D2 FAIL and D3 FAIL |
| W-F4 | Object-level isolation (A01) | `wger/manager/api/views.py` RoutineViewSet.get_queryset: replace the owner/public filter with `Q()` | D4 FAIL (private routine of another user visible in the list) |
| W-F5 | Object write permission (A01) | `wger/manager/api/permissions.py` RoutinePermission.has_object_permission: replace `return request.method in permissions.SAFE_METHODS` with `return True` | D5 FAIL (other user PATCHes a public template) |
| W-F7 | Security headers (A02/A05) | append `SECURE_CONTENT_TYPE_NOSNIFF = False` to `settings/main.py` | D7 FAIL (X-Content-Type-Options missing) |
| W-F8 | Debug disabled (A02/A05) | environment DJANGO_DEBUG=1 | D8 FAIL |

Not injected: D1 (token revocation at logout). Revocation is implemented in the third-party django-allauth
library, not in wger code; D1 is evaluated on the unmodified code only (expected PASS).
D6 (password-reset oracle): the oracle is not applicable to this configuration unless a reset endpoint is
reachable through the API; reported as found.

Detectors and oracles (D1-D8) are those of `replication/fi_targets.py` at the time of writing; only the
target adapter (URLs, request bodies) is added for wger. Any change to an oracle after seeing wger results
will be reported as a deviation.
