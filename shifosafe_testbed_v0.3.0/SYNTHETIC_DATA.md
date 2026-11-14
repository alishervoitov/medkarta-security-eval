# Synthetic data used in the experiments

No real patient data were used or copied. The demonstration database was filled by a generator (management command `seed_demo`, not distributed because it is part of the closed application). This file describes it so that an equivalent data set can be rebuilt.

| Item | Specification |
|---|---|
| Doctors | 4 accounts `doctor1`–`doctor4`, e-mail `<username>@example.com`, fixed Uzbek names |
| Patients | N accounts (default 20) `patient01`…, e-mail `<username>@example.com`; first name drawn from 10 male / 10 female names, surname from 10 surnames (female form adds "a") |
| Passwords | random 14 characters (letters and digits) per account, printed once, not stored |
| Patient profile | date of birth: age 3–85; gender M/F; blood group from 8 values; allergies from a short list (often empty); national id `DEMO-000001`…; address "<city>, <n>-uy" from 6 cities; primary doctor assigned round-robin |
| Medical records | 1–3 per patient, drawn from 5 templates (diagnosis, visit, lab result, procedure); visit date 1–400 days back |
| Prescriptions | with probability 0.6, one per patient, drawn from 5 medications; start date 0–40 days back |
| Generation time | one run, 24 accounts in 7.8 s (2026-10-17) |
| Fault-injection copy | a smaller seed: 2 doctors and 3 patients (`patient01` and `patient02` with 2 records each, `patient20` without records, used for the lockout test); password is a throw-away value valid only for the 127.0.0.1 copy |

Further accounts on the demonstration system belong to the author's acquaintances, who agreed to take part; their medical records are fictitious. These accounts were not used by any detector.
