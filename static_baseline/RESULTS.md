# Static-analysis baseline (Bandit 1.9.4, Semgrep 1.181.0)

Run on all 24 code states (BASE, fault-injected, repaired) of the five projects.
Bandit: default rule set, tests/migrations/docs excluded.
Semgrep: community rules `python/django/security`, `python/django/best-practice`, `python/lang/security`,
`python/jwt` from github.com/semgrep/semgrep-rules commit 17e31e11ebac99fb7dfe1cd288f7a32151b6f3f9
(the semgrep.dev registry was unreachable from the execution environment). Metrics off.
Comparison key: (file, rule id) per finding, location-insensitive; each fault state is diffed against its BASE.

## Result 1: injected faults
New findings relative to BASE, over all 19 non-BASE states (17 fault states, 2 repaired states): **Bandit 0, Semgrep 0**. Totals are identical
to BASE in every state (Bandit/Semgrep): authorization_api 4/8, b2c-system 5/7, healthcare-backend 6/3,
wger 116/120, Tandoor 72/46. Neither tool noticed any of the injected faults
(logout blacklist removed, throttling disabled, queryset widened, permission relaxed, nosniff off, DEBUG on).
The fault-injection detectors flagged all 16 informative faults among these 17 fault states (W-F7 was uninformative, see PROTOCOL/README).

## Result 2: natural findings on the author's projects
Semgrep `missing-throttle-config` fired on settings of authorization_api and b2c-system, consistent with
detector D2 = FAIL there. Other findings (hardcoded SECRET_KEY / `unvalidated-password` / `use-defused-xml`)
are not covered by D1-D8. Neither tool reported: missing token revocation (D1), missing lockout (D3),
existence oracle (D6), DEBUG=True (D8), password echo (X2), early token issue (X1).

## Caveat
Static tools address a different question (code patterns) and are not designed to check runtime effectiveness
of controls; the comparison shows complementarity, not that they are poor tools. Rule sets are community
defaults; custom rules could cover some single patterns (e.g. `throttle_classes = []`).
