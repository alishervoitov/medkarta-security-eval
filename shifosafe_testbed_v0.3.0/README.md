# ShifoSafe test bed (supplement to the v0.2.0 package, proposed v0.3.0)

Paper: "Evaluating State-Aware Security Tests for Django REST Framework Applications: Fault Injection and an Independent Penetration Test".
Main package: https://github.com/alishervoitov/medkarta-security-eval (Zenodo concept DOI 10.5281/zenodo.23466229).

## What is and is not here
The ShifoSafe application (named MedKarta in repository names) is a medical system and its source is not distributed. This folder provides everything around it that is not secret, so that the setup, the data and the expected outcomes can be checked and an equivalent system rebuilt:

| File | Content |
|---|---|
| `docker-compose.testbed.yml` | sanitised Compose file (127.0.0.1 only, no public ports, no Caddy) |
| `env.testbed.example` | all environment variables with placeholders; no secrets |
| `nginx.conf` | the real front-end proxy configuration (security headers checked by D7) |
| `VERSIONS.md` | pinned versions of every component |
| `SYNTHETIC_DATA.md` | specification of the synthetic data set |
| `DETECTORS.md` | request sequences, firing conditions and healthy-state answers of D1–D8 and D1′ |
| `EXPECTED_RESULTS.md` | expected detector × configuration matrix and reference numbers |
| `d1_experiment/` | D1/D1′ experiment (`d1_expired_token.py`), its raw results and `metrics.py` (rates and Clopper–Pearson intervals) |

## Reproduction path
1. Prepare a Django/DRF application that exposes the endpoints named in `DETECTORS.md` (the detectors are written against `/api/auth/*` and `/api/records/medical-records/`). For other projects use the adapter pattern in `replication/fi_targets.py` of the v0.2.0 package.
2. Copy `env.testbed.example` to `.env.testbed`, generate fresh secrets, keep `DEBUG=0`.
3. Start the stack under its own project name: `docker compose -p fi -f docker-compose.testbed.yml --env-file .env.testbed up -d --build`.
4. Run `fault_injection/fi_run.py BASE --no-zap`; all detectors must be silent. Then run the faults (`F1`…`F8`) and compare with `EXPECTED_RESULTS.md`.
5. For D1/D1′ run `d1_experiment/d1_expired_token.py` (minimal Django, DRF and SimpleJWT project; no ShifoSafe code needed) and compare with `d1_results.jsonl`.
6. `d1_experiment/metrics.py` recomputes the detection and alarm rates from the result files.

## Safety
Everything runs on 127.0.0.1 in a project of its own and must never be pointed at a system you do not own. No real patient data are used (see `SYNTHETIC_DATA.md`).

## Limits
Without the ShifoSafe source the full ShifoSafe configuration (F1–F8 on the original code) cannot be re-run exactly; the replication on wger, Tandoor and the other projects and the D1/D1′ experiment can be reproduced completely from public material.
