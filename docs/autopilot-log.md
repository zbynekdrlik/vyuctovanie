# Autopilot log

Terse per-ticket record: issue #, commit SHAs, RED→GREEN test names, decisions, PR #.

## #16 — Prázdny popis položky: vziať popis z nasledujúcich riadkov správy

- Bump 1.6.1 → 1.7.0: `4cb54fb`
- RED: `53880a5` — 8 new tests in `tests/test_parsing.py` (`test_parse_entries_bare_hour_line_takes_description_from_following_bullets` + 7 more), all failing before the fix
- GREEN: `b278129` — `parse_entries` (vyuct/parsing.py) tracks the last description-less hour entry (`pending`) and joins following non-empty lines onto it (leading `-`/`–` stripped, whitespace collapsed) via `; `, up to the next hour line or end of message; hour lines with a same-line description are unaffected
- Decision: continuation attaches to the nearest preceding description-less hour line, never truncated to just the first following line (rejected — loses multi-bullet info for no benefit)
- PR #17 → master merge `4f33760`, all gates green (CI, review 0🔴0🟡0🔵, 105/105 tests)
- Deployed: prod checkout `~/devel/vyuctovanie` pulled to `4f33760`, verified `__version__ == '1.7.0'` + functional check + pytest 105/105 in prod checkout

## #19 — Pokračovacie riadky bez odrážky spájať medzerou, nie bodkočiarkou (follow-up k #16)

- Bump 1.7.1 → 1.7.2: `8ec3c03`
- RED: `b7205eb` — 4 new tests in `tests/test_parsing.py` (wrapped line inside a bullet, multiple bullets each with own wrap, continuation with no leading bullet at all, `•` bullet marker), all failing before the fix
- GREEN: `cbd073c` — `parse_entries` (vyuct/parsing.py) collector made bullet-aware: a line starting with `-`/`–`/`•` starts a new fragment (marker stripped, as #16); a non-bullet line is a manual word-wrap and appends to the CURRENT fragment with a single space; fragments join with `; `
- Decision: track fragments as a list (`frags`) instead of tail-inspecting the accumulated string, since the accumulated text can legitimately contain "; " already
- PR #20 → master merge `a119918`, all gates green (CI, review 0🔴0🟡0🔵, 109/109 tests)
- Deployed: prod checkout `~/devel/vyuctovanie` pulled to `a119918`, verified `__version__ == '1.7.2'` + issue's own example now produces the expected space-joined text + pytest 109/109 in prod checkout

## #23 — Obdobie vyúčtovania: názov mesiaca namiesto rozsahu dátumov

- Bump 1.7.4 → 1.8.0: `8b131fe`
- RED: `e15705e` — 13 new tests (`tests/test_render.py`: `test_period_label_*` ×5, `test_render_settlement_uses_month_label_*`, `test_render_settlement_uses_date_range_*`; `tests/test_xlsx.py`: updated title/sheet assertions + `test_filename_*` ×3), all failing before the fix (import error, then wrong assertions)
- GREEN: `fbc87af` — `period_label(items, od, do)` in `vyuct/render.py` (+ `_MONTHS_SK` tuple): all item dates same (year, month) → `"<mesiac> <rok>"`, else fallback `od → do` range. Used in `render()` settlement body, `xlsx.build_xlsx` A1 title + sheet name, `xlsx.xlsx_filename`. `xlsx.py` imports from `render.py` (one-directional).
- Review fixes: `6ce4eb6` (self-review — extracted shared `single_month()` helper instead of string-sniffing the label for the fallback branch), `b1e2c38` (deep-review 🔵×3 — compute `period_label` once in `build_xlsx`, added empty-items sheet/A1 fallback test, added order-independence test for `single_month`)
- Decision: month decided by item dates, NOT by `od`/`do` boundaries — `do` is the closing date (typically 1st of next month), so the uzávierka→uzávierka range formally always crosses a month boundary; deciding from `od`/`do` was explicitly rejected in the issue itself.
- PR #24 → master, 122/122 tests, 100% coverage on render.py + xlsx.py
