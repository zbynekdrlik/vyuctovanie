---
paths:
  - "vyuct/xlsx.py"
  - "tests/test_xlsx.py"
---

# openpyxl — gotchas (výkaz #13)

- **Injektáž vzorca:** openpyxl uloží string-hodnotu bunky začínajúcu `=` ako FORMULU (`data_type='f'`) a Excel ju vykoná. Popis položiek pochádza zo správ kanála (nedôveryhodný vstup), takže bunku popisu vynúť na text: `if isinstance(v, str) and v.startswith('='): c.data_type = 's'` (hodnota ostane presne rovnaká, len sa neinterpretuje ako vzorec). Regresný test to overuje cez `data_type`.
- **Zdieľateľné štýly:** `Font`/`Alignment`/`PatternFill` sú immutable a zdieľateľné — jednu inštanciu (`_DATA_FONT = Font(size=10)`) priraď mnohým bunkám, nevyrábaj novú per bunka.
- **Názov hárku:** max 31 znakov, zakázané `[ ] : * ? / \`. Sanitizuj cez samostatný `_sanitize_sheet_name(raw)` (testovateľný priamo adverzariálnym stringom — z reálnych dátumov sa zakázaný znak nikdy nevyskytne, takže test cez celý workbook by logiku sanitizéra nepokryl).
- **`=SUM` pri prázdnych položkách:** SPOLU riadok ide hneď pod hlavičku (riadok 5) a musí byť literálna `0`, nie self-referenčný `=SUM(B5:B5)`.
- Verifikácia vygenerovaného súboru: `openpyxl.load_workbook(io.BytesIO(data))` a čítaj bunky/`number_format`/`fill.fgColor.rgb` (ARGB s alfa `FF…`) späť.
