---
paths:
  - "vyuct/xlsx.py"
  - "vyuct/render.py"
  - "tests/test_xlsx.py"
  - "tests/test_render.py"
---

# openpyxl — gotchas (výkaz #13)

- **Injektáž vzorca:** openpyxl uloží string-hodnotu bunky začínajúcu `=` ako FORMULU (`data_type='f'`) a Excel ju vykoná. Popis položiek pochádza zo správ kanála (nedôveryhodný vstup), takže bunku popisu vynúť na text: `if isinstance(v, str) and v.startswith('='): c.data_type = 's'` (hodnota ostane presne rovnaká, len sa neinterpretuje ako vzorec). Regresný test to overuje cez `data_type`.
- **Zdieľateľné štýly:** `Font`/`Alignment`/`PatternFill` sú immutable a zdieľateľné — jednu inštanciu (`_DATA_FONT = Font(size=10)`) priraď mnohým bunkám, nevyrábaj novú per bunka.
- **Názov hárku:** max 31 znakov, zakázané `[ ] : * ? / \`. Sanitizuj cez samostatný `_sanitize_sheet_name(raw)` (testovateľný priamo adverzariálnym stringom — z reálnych dátumov sa zakázaný znak nikdy nevyskytne, takže test cez celý workbook by logiku sanitizéra nepokryl).
- **`=SUM` pri prázdnych položkách:** SPOLU riadok ide hneď pod hlavičku (riadok 5) a musí byť literálna `0`, nie self-referenčný `=SUM(B5:B5)`.
- Verifikácia vygenerovaného súboru: `openpyxl.load_workbook(io.BytesIO(data))` a čítaj bunky/`number_format`/`fill.fgColor.rgb` (ARGB s alfa `FF…`) späť.
- **Obdobie (#23):** `period_label(items, od, do)` + `single_month(items)` žijú v `vyuct/render.py` (nie v `xlsx.py`) — `xlsx.py` ich importuje jednosmerne (`from .render import period_label, single_month`). Rozhoduje mesiac REÁLNYCH POLOŽIEK (`items`), nikdy `od`/`do` — `do` je dátum uzávierky, typicky 1. deň nasledujúceho mesiaca, takže rozsah uzávierka→uzávierka formálne vždy prechádza cez prelom mesiaca aj keď všetky odrobené hodiny padnú do jedného mesiaca. Pri viacnásobnom použití labelu v jednej funkcii (`build_xlsx`) počítaj `period_label`/`single_month` RAZ a zdieľaj výsledok (title aj A1) — nerátaj ho pre každé miesto zvlášť. `xlsx_filename` vetví na `single_month(items)` (explicitná (rok,mesiac) kontrola), nikdy na obsahu vráteného stringu (napr. hľadaním `' → '` v labeli) — string-sniffing je krehká väzba na presný formát `period_label`.
