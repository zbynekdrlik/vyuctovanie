# Autopilot log

Terse per-ticket record: issue #, commit SHAs, RED→GREEN test names, decisions, PR #.

## #16 — Prázdny popis položky: vziať popis z nasledujúcich riadkov správy

- Bump 1.6.1 → 1.7.0: `4cb54fb`
- RED: `53880a5` — 8 new tests in `tests/test_parsing.py` (`test_parse_entries_bare_hour_line_takes_description_from_following_bullets` + 7 more), all failing before the fix
- GREEN: `b278129` — `parse_entries` (vyuct/parsing.py) tracks the last description-less hour entry (`pending`) and joins following non-empty lines onto it (leading `-`/`–` stripped, whitespace collapsed) via `; `, up to the next hour line or end of message; hour lines with a same-line description are unaffected
- Decision: continuation attaches to the nearest preceding description-less hour line, never truncated to just the first following line (rejected — loses multi-bullet info for no benefit)
- PR #17 → master merge `4f33760`, all gates green (CI, review 0🔴0🟡0🔵, 105/105 tests)
- Deployed: prod checkout `~/devel/vyuctovanie` pulled to `4f33760`, verified `__version__ == '1.7.0'` + functional check + pytest 105/105 in prod checkout
