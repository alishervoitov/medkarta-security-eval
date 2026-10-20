# Pre-registered fault list: TandoorRecipes/recipes (written before any Tandoor fault run)

Date: 2026-10-20. Target: shallow clone of master as of 2026-10-20 (last upstream commit 2026-10-19).
Run configuration: SQLite, DEBUG off, python-ldap omitted (LDAP not used), `DJANGO_SETTINGS_MODULE=recipes.settings`
set from the environment (the clone's manage.py default `recipe.settings` does not exist).
Actors: alice = admin of space A; bob = guest in space A; carol = admin of an unrelated space B; dave = logout test.
Baseline expectation: all of D1-D5, D7, D8 PASS on unmodified code. If a baseline result differs it is reported as found.

| ID | Control (OWASP) | Injection | Expected detector flip |
|----|-----------------|-----------|------------------------|
| T-F2 | Login rate limiting (A07) | append `ACCOUNT_RATE_LIMITS = False` to `recipes/settings.py` | D2 FAIL and D3 FAIL |
| T-F4 | Tenant (space) isolation (A01) | two-layer fault: (a) `cookbook/helper/scope_middleware.py` API branch `with scope(space=request.space):` -> `with scopes_disabled():`; (b) `cookbook/views/api.py` RecipeViewSet list queryset `space=self.request.space` filter -> `pk__gt=0` | D4 FAIL (recipe of another space visible in the list) |
| T-F5 | Role-based write permission (A01) | `cookbook/helper/permission_helper.py` CustomRecipePermission (both methods): drop `and request.method in SAFE_METHODS` for the guest group | D5 FAIL (guest PATCHes a recipe) |
| T-F7 | Security headers (A02/A05) | append `SECURE_CONTENT_TYPE_NOSNIFF = False` to `recipes/settings.py` | D7 FAIL |
| T-F8 | Debug disabled (A02/A05) | environment DEBUG=1 | D8 FAIL |

Not injected: D1 (session token revocation at logout): implemented in third-party django-allauth; evaluated on
unmodified code only (expected PASS). D6: no password-reset oracle exercised (not applicable via the API in
this configuration).
Why two layers in T-F4/T-F5: the code enforces isolation / roles redundantly (django-scopes manager, explicit
filter, object permission); a single-layer fault would be masked. The compound fault is declared in advance.

Detectors and oracles (D1-D8) are those of `replication/fi_targets.py` as used for wger; only the target adapter
(URLs, request bodies, session-token header) is added. Any oracle change after seeing Tandoor results is reported
as a deviation.
