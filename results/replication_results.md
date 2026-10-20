| Condition | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | X1 | X2 |
|---|---|---|---|---|---|---|---|---|---|---|
| authorization_api/BASE | ABSENT | FAIL | FAIL | PASS | N/A | FAIL | PASS | FAIL | FAIL | FAIL |
| authorization_api/REPAIR | ABSENT | PASS | FAIL | PASS | N/A | FAIL | PASS | PASS | FAIL | FAIL |
| b2c-system/BASE | ABSENT | FAIL | FAIL | PASS | N/A | FAIL | PASS | FAIL | FAIL | FAIL |
| b2c-system/REPAIR | ABSENT | PASS | FAIL | PASS | N/A | FAIL | PASS | PASS | FAIL | FAIL |
| b2c-system/FAULT_D4 | ABSENT | PASS | FAIL | FAIL | N/A | FAIL | PASS | PASS | FAIL | FAIL |
| healthcare-backend/BASE | PASS | PASS | FAIL | PASS | PASS | N/A | PASS | PASS | N/A | PASS |
| healthcare-backend/F1_logout | FAIL | PASS | FAIL | PASS | PASS | N/A | PASS | PASS | N/A | PASS |
| healthcare-backend/F2_throttle | PASS | FAIL | FAIL | PASS | PASS | N/A | PASS | PASS | N/A | PASS |
| healthcare-backend/F4_idor | PASS | PASS | FAIL | FAIL | PASS | N/A | PASS | PASS | N/A | PASS |
| healthcare-backend/F5_objperm | PASS | PASS | FAIL | PASS | FAIL | N/A | PASS | PASS | N/A | PASS |
| healthcare-backend/F7_headers | PASS | PASS | FAIL | PASS | PASS | N/A | FAIL | PASS | N/A | PASS |
| healthcare-backend/F8_debug | PASS | PASS | FAIL | PASS | PASS | N/A | PASS | FAIL | N/A | PASS |
| wger/BASE | PASS | PASS | PASS | PASS | PASS | N/A | FAIL | PASS | N/A | N/A |
| wger/W_F2_axes_off | PASS | FAIL | FAIL | PASS | PASS | N/A | FAIL | PASS | N/A | N/A |
| wger/W_F4_idor | PASS | PASS | PASS | FAIL | PASS | N/A | FAIL | PASS | N/A | N/A |
| wger/W_F5_objperm | PASS | PASS | PASS | PASS | FAIL | N/A | FAIL | PASS | N/A | N/A |
| wger/W_F7_headers | PASS | PASS | PASS | PASS | PASS | N/A | FAIL | PASS | N/A | N/A |
| wger/W_F8_debug | PASS | PASS | PASS | PASS | PASS | N/A | FAIL | FAIL | N/A | N/A |
| tandoor/BASE | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | N/A | N/A |
| tandoor/T_F2_ratelimit_off | PASS | FAIL | FAIL | PASS | PASS | N/A | PASS | PASS | N/A | N/A |
| tandoor/T_F4_space_isolation | PASS | PASS | PASS | FAIL | PASS | N/A | PASS | PASS | N/A | N/A |
| tandoor/T_F5_guest_write | PASS | PASS | PASS | PASS | FAIL | N/A | PASS | PASS | N/A | N/A |
| tandoor/T_F7_headers | PASS | PASS | PASS | PASS | PASS | N/A | FAIL | PASS | N/A | N/A |
| tandoor/T_F8_debug | PASS | PASS | PASS | PASS | PASS | N/A | PASS | FAIL | N/A | N/A |

### authorization_api/BASE
- D1 ABSENT: no logout endpoint; refresh token stays usable (refresh=200)
- D2 FAIL: 40 failed logins -> 429 x0, others [404]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: PUT edit-profile/ -> 200; PUT edit-profile/2/ -> 404; bob.full_name='bob'
- D5 N/A: no shared record with owner-only write access in the target
- D6 FAIL: existing e-mail -> 200, unknown e-mail -> 500
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 FAIL: 404 page -> 404, debug trace present
- X1 FAIL: unverified user's token on user_profile -> 200
- X2 FAIL: plaintext password echoed in register response (200)

### authorization_api/REPAIR
- D1 ABSENT: no logout endpoint; refresh token stays usable (refresh=200)
- D2 PASS: 40 failed logins -> 429 x25, others [404]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: PUT edit-profile/ -> 200; PUT edit-profile/2/ -> 404; bob.full_name='bob'
- D5 N/A: no shared record with owner-only write access in the target
- D6 FAIL: existing e-mail -> 200, unknown e-mail -> 500
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 FAIL: unverified user's token on user_profile -> 200
- X2 FAIL: plaintext password echoed in register response (200)

### b2c-system/BASE
- D1 ABSENT: no logout endpoint; refresh token stays usable (refresh=200)
- D2 FAIL: 40 failed logins -> 429 x0, others [500]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice add-item=201; bob lists cart -> 0 item(s) (expected 0)
- D5 N/A: no shared record with owner-only write access in the target
- D6 FAIL: existing e-mail -> 200, unknown e-mail -> 500
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 FAIL: 404 page -> 404, debug trace present
- X1 FAIL: unverified user's token on user_profile -> 200
- X2 FAIL: plaintext password echoed in register response (200)

### b2c-system/REPAIR
- D1 ABSENT: no logout endpoint; refresh token stays usable (refresh=200)
- D2 PASS: 40 failed logins -> 429 x25, others [500]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice add-item=201; bob lists cart -> 0 item(s) (expected 0)
- D5 N/A: no shared record with owner-only write access in the target
- D6 FAIL: existing e-mail -> 200, unknown e-mail -> 500
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 FAIL: unverified user's token on user_profile -> 200
- X2 FAIL: plaintext password echoed in register response (200)

### b2c-system/FAULT_D4
- D1 ABSENT: no logout endpoint; refresh token stays usable (refresh=200)
- D2 PASS: 40 failed logins -> 429 x25, others [500]
- D3 FAIL: correct password after 6 failures -> 200
- D4 FAIL: alice add-item=201; bob lists cart -> 1 item(s) (expected 0)
- D5 N/A: no shared record with owner-only write access in the target
- D6 FAIL: existing e-mail -> 200, unknown e-mail -> 500
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 FAIL: unverified user's token on user_profile -> 200
- X2 FAIL: plaintext password echoed in register response (200)

### healthcare-backend/BASE
- D1 PASS: logout=205; refresh after logout=401 (expected 401)
- D2 PASS: 40 failed logins -> 429 x37, others [401]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice creates record 1; bob GET it -> 404 (expected 404)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 N/A: target has no e-mail verification step
- X2 PASS: plaintext password not present in register response (201)

### healthcare-backend/F1_logout
- D1 FAIL: logout=205; refresh after logout=200 (expected 401)
- D2 PASS: 40 failed logins -> 429 x37, others [401]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice creates record 1; bob GET it -> 404 (expected 404)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 N/A: target has no e-mail verification step
- X2 PASS: plaintext password not present in register response (201)

### healthcare-backend/F2_throttle
- D1 PASS: logout=205; refresh after logout=401 (expected 401)
- D2 FAIL: 40 failed logins -> 429 x0, others [401]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice creates record 1; bob GET it -> 404 (expected 404)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 N/A: target has no e-mail verification step
- X2 PASS: plaintext password not present in register response (201)

### healthcare-backend/F4_idor
- D1 PASS: logout=205; refresh after logout=401 (expected 401)
- D2 PASS: 40 failed logins -> 429 x37, others [401]
- D3 FAIL: correct password after 6 failures -> 200
- D4 FAIL: alice creates record 1; bob GET it -> 200 (expected 404)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 N/A: target has no e-mail verification step
- X2 PASS: plaintext password not present in register response (201)

### healthcare-backend/F5_objperm
- D1 PASS: logout=205; refresh after logout=401 (expected 401)
- D2 PASS: 40 failed logins -> 429 x37, others [401]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice creates record 1; bob GET it -> 404 (expected 404)
- D5 FAIL: alice creates record 1; bob PATCH it -> 200 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 N/A: target has no e-mail verification step
- X2 PASS: plaintext password not present in register response (201)

### healthcare-backend/F7_headers
- D1 PASS: logout=205; refresh after logout=401 (expected 401)
- D2 PASS: 40 failed logins -> 429 x37, others [401]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice creates record 1; bob GET it -> 404 (expected 404)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 404, debug trace absent
- X1 N/A: target has no e-mail verification step
- X2 PASS: plaintext password not present in register response (201)

### healthcare-backend/F8_debug
- D1 PASS: logout=205; refresh after logout=401 (expected 401)
- D2 PASS: 40 failed logins -> 429 x37, others [401]
- D3 FAIL: correct password after 6 failures -> 200
- D4 PASS: alice creates record 1; bob GET it -> 404 (expected 404)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 FAIL: 404 page -> 404, debug trace present
- X1 N/A: target has no e-mail verification step
- X2 PASS: plaintext password not present in register response (201)

### wger/BASE
- D1 PASS: logout=401 (accepted codes [200, 204, 401]); refresh after logout=400 (expected rejection)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; bob GET it -> 404, record in bob's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options, Referrer-Policy (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### wger/W_F2_axes_off
- D1 PASS: logout=401 (accepted codes [200, 204, 401]); refresh after logout=400 (expected rejection)
- D2 FAIL: 40 failed logins -> 429 x0, others [400]
- D3 FAIL: correct password after 12 failures -> 200
- D4 PASS: alice creates record 2; bob GET it -> 404, record in bob's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options, Referrer-Policy (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### wger/W_F4_idor
- D1 PASS: logout=401 (accepted codes [200, 204, 401]); refresh after logout=400 (expected rejection)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 FAIL: alice creates record 2; bob GET it -> 403, record in bob's list: True (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options, Referrer-Policy (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### wger/W_F5_objperm
- D1 PASS: logout=401 (accepted codes [200, 204, 401]); refresh after logout=400 (expected rejection)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; bob GET it -> 404, record in bob's list: False (expected 404/403, absent)
- D5 FAIL: alice creates record 1; bob PATCH it -> 200 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options, Referrer-Policy (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### wger/W_F7_headers
- D1 PASS: logout=401 (accepted codes [200, 204, 401]); refresh after logout=400 (expected rejection)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; bob GET it -> 404, record in bob's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options, Referrer-Policy (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### wger/W_F8_debug
- D1 PASS: logout=401 (accepted codes [200, 204, 401]); refresh after logout=400 (expected rejection)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; bob GET it -> 404, record in bob's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options, Referrer-Policy (CSP absent, noted but not scored)
- D8 FAIL: 404 page -> 404, debug trace present
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### tandoor/BASE
- D1 PASS: logout=401; same session token after logout -> 403 (expected 401/403)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; carol GET it -> 404, record in carol's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### tandoor/T_F2_ratelimit_off
- D1 PASS: logout=401; same session token after logout -> 403 (expected 401/403)
- D2 FAIL: 40 failed logins -> 429 x0, others [400]
- D3 FAIL: correct password after 12 failures -> 200
- D4 PASS: alice creates record 2; carol GET it -> 404, record in carol's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### tandoor/T_F4_space_isolation
- D1 PASS: logout=401; same session token after logout -> 403 (expected 401/403)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 FAIL: alice creates record 2; carol GET it -> 404, record in carol's list: True (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### tandoor/T_F5_guest_write
- D1 PASS: logout=401; same session token after logout -> 403 (expected 401/403)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; carol GET it -> 404, record in carol's list: False (expected 404/403, absent)
- D5 FAIL: alice creates record 1; bob PATCH it -> 200 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### tandoor/T_F7_headers
- D1 PASS: logout=401; same session token after logout -> 403 (expected 401/403)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; carol GET it -> 404, record in carol's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 FAIL: missing: X-Content-Type-Options (CSP absent, noted but not scored)
- D8 PASS: 404 page -> 500, debug trace absent
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target

### tandoor/T_F8_debug
- D1 PASS: logout=401; same session token after logout -> 403 (expected 401/403)
- D2 PASS: 40 failed logins -> 429 x40, others []
- D3 PASS: correct password after 12 failures -> 429
- D4 PASS: alice creates record 2; carol GET it -> 404, record in carol's list: False (expected 404/403, absent)
- D5 PASS: alice creates record 1; bob PATCH it -> 403 (expected 403)
- D6 N/A: no password-reset endpoint
- D7 PASS: missing: none (CSP absent, noted but not scored)
- D8 FAIL: 404 page -> 500, debug trace present
- X1 N/A: registration not exercised for this target
- X2 N/A: registration not exercised for this target
