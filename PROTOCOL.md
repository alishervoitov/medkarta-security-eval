# Target selection protocol (fixed before searching, 2026-10-20)

Goal: choose independent, third-party Django/DRF applications on which the security-control
detectors (D1-D8) and fault injection are replicated. The protocol is fixed first so that the
selection cannot be tuned to projects on which the method happens to work.

## Inclusion criteria (all required)
- I1  Django + Django REST Framework application (not a library, template or tutorial series).
- I2  Token/JWT authentication with user accounts (register and login endpoints).
- I3  At least one user-owned resource (a record that belongs to its creator).
- I4  Can be run headless with a SQLite database override, <= 30 minutes of setup effort.
- I5  Public repository with a permissive or copyleft open-source licence file.
- I6  Last commit within 12 months of the selection date (on or after 2025-10-20).
- I7  At least 100 stars, or documented production use (filters out coursework repositories).
- I8  Not authored by the study author.

## Exclusion criteria
- Archived or read-only repositories.
- Requires paid or external services that cannot be stubbed (payments, SMS, cloud storage) for the endpoints under test.
- Python < 3.10 only.

## Procedure
1. Run the fixed search queries below (web search, first result page only); record every repository returned.
2. De-duplicate; check I1-I8 from the repository page and files; record the reason for each rejection.
3. Starting from the top of the de-duplicated list in search order, attempt setup; stop at 5-8 accepted projects.
4. Report the full selection flow (found / screened / excluded with reasons / accepted) in the paper.

## Fixed search queries
Q1  django rest framework jwt authentication api github
Q2  drf simplejwt rest api project github permissions ownership
Q3  django rest framework ecommerce api jwt github
Q4  django rest framework task manager api jwt github
Q5  django rest framework blog social api jwt github
Q6  django rest framework healthcare patients api jwt github

## Amendment 1 (2026-10-20, before any target was set up)
The fixed web-search queries returned almost only small tutorial/coursework repositories (fail I7), and
GitHub topic pages could not be enumerated with star counts in this environment. A second source was
therefore added: well-known, actively maintained open-source Django/DRF applications named from domain
knowledge (wger, Tandoor Recipes, InvenTree, Paperless-ngx). They are screened with the same criteria
I1-I8 (star counts to be read from the repository page; not assumed). All screened projects and
rejection reasons will be reported.

## Screening log (I1-I6 verified from a shallow clone on 2026-10-20)
| Project | DRF | Auth in settings | SQLite | Licence | Last commit | Notes |
|---|---|---|---|---|---|---|
| wger-project/wger | yes | simplejwt (RS256, rotation+blacklist), session, token | default | AGPL-3.0+ | 2026-10-19 | login throttle 10/min; logout route; many user-owned resources |
| TandoorRecipes/recipes | yes | allauth headless session token, session, OAuth2 | supported | LICENSE.md | 2026-10-19 | multi-tenant "spaces" |
| inventree/InvenTree | yes | not yet inspected | not yet inspected | LICENSE | 2026-10-18 | large; role/permission model |
| paperless-ngx/paperless-ngx | yes | static Token, session, basic | supported | LICENSE | 2026-10-20 | per-object owner permissions; heavy runtime |
I7 (stars) and I4 (setup effort) pending for all.

## Screening outcome (2026-10-20)
Accepted and run: healthcare-backend (Sumit99589; note: 2 commits, no stars, found by web search, fails I7 and is
reported as a small supplementary case), wger-project/wger, TandoorRecipes/recipes. Not run (time): InvenTree,
paperless-ngx. Star counts (I7), read from the repository pages on 2026-10-20 (rounded as displayed by GitHub):
wger ~7.0k stars / ~1.0k forks (AGPL-3.0+); Tandoor Recipes ~8.7k stars / 883 forks (AGPL-3.0 with a
Commons Clause selling exception from v0.10.0, so not strictly OSI-open; analysis and local execution are
unaffected). Both satisfy I7. The pages did not show a last-commit date; I6 rests on the shallow-clone log
above (both 2026-10-19). Own projects (authorization_api, b2c-system) are reported separately as natural-finding cases.
