# vyuctovanie — automatické vyúčtovanie hodín z Odoo chatu

Malá lokálna appka (bez servera), nasadzovaná pre viacero zákazníkov: číta Odoo Discuss
kanál výkazov daného zákazníka, extrahuje hodiny zo správ (`- 4h`, `- 1,5h popis`,
`- 3 hodiny`) a posiela do toho istého kanála:

- **VYÚČTOVANIE** hneď po správe „uzavierka" (rozpis podľa ľudí — položky + medzisúčet v h na osobu; celkový súčet od predošlej uzávierky v h aj €; potom sa počíta od nuly)
- **Priebežné info** o 20:00 (okno 20:00–20:59; hodiny zapísané po 20:00 idú do info nasledujúci deň), max 1× denne, len ak pribudli nové hodiny — súčet od poslednej uzávierky, sadzba podľa `VYUCT_RATE_EUR`/`VYUCT_RATES`

Stav sa neodkladá lokálne — odvodzuje sa z histórie kanála (idempotentné behy).

**Hodiny za iného človeka (prefix „Meno:"):** ak je PRVÝ neprázdny riadok správy tvaru
`Meno:` (krátky text ≤ 40 znakov, nezačína `-`, nie je riadok hodín, končí dvojbodkou),
všetky položky tej správy sa počítajú pod `Meno` namiesto autora správy — na zápis hodín
za niekoho, kto v kanáli sám nepíše. Sadzba pre `Meno` sa berie z `VYUCT_RATES` (fallback
`VYUCT_RATE_EUR`). O prefixe rozhoduje iba prvý neprázdny riadok. Príklad:

    Meno:
    - 6h návrh výkresu

## Súbory

- `vyuctovanie.py` — tenký vstupný bod (systemd ho spúšťa)
- `vyuct/` — moduly: `config.py` (nastavenia), `parsing.py` (extrakcia hodín), `logic.py` (rozhodovanie), `render.py` (formát správ), `odoo.py` (JSON-2 klient), `cli.py` (orchestrácia)
- `tests/` — `python3 -m pytest tests/ -v`
- `vyuctovanie@.{service,timer}` — systemd user template units (inštancia na zákazníka), beh každých 10 min
- `vyuctovanie-fail@.service` — OnFailure alert unit (zlyhaný beh → notifikácia)

## Prevádzka — viac zákazníkov (jedna appka, N inštancií)

Jeden kód, jedna inštancia timera na zákazníka — všetci bežia z tohto checkoutu,
takže fix v kóde platí okamžite pre všetkých.

- Config zákazníka: `~/.config/vyuct/<meno>.env` (systemd `EnvironmentFile`, MIMO git):
  `ODOO_URL`, `ODOO_DB`, `ODOO_KEY_FILE` (absolútna cesta, mode 600), `ODOO_BOT_LOGIN`,
  `VYUCT_CHANNEL_ID`, `VYUCT_RATE_EUR`, voliteľné VYUCT_RATES („Meno=15;Iné Meno=40“ —
  sadzba per osoba, má prednosť pred VYUCT_RATE_EUR)
- Nový zákazník: (1) v jeho Odoo vytvor bot používateľa + API kľúč a pozvi bota do
  kanála výkazov; (2) kľúč ulož do súboru (mode 600) a vytvor `~/.config/vyuct/<meno>.env`;
  (3) `systemctl --user enable --now vyuctovanie@<meno>.timer`
- Inštalácia units (raz): `ln -sf` `vyuctovanie@.{service,timer}` do
  `~/.config/systemd/user/`, potom `systemctl --user daemon-reload`
- Logy: `journalctl --user -u vyuctovanie@<meno>.service`
- Manuálny beh: `set -a; . ~/.config/vyuct/<meno>.env; set +a; python3 vyuctovanie.py`
  s voľbami `--dry-run` (nič nepošle), `--force-info` (pošle info hneď), `--channel N`;
  hodnoty s medzerami v env súbore (napr. `VYUCT_RATES`) daj do úvodzoviek
- Lock je per-inštancia (host+kanál) — zákazníci sa navzájom neblokujú

## Git & deploy

- Repo: github.com/zbynekdrlik/vyuctovanie (verejné — žiadne zákaznícke údaje do repa!). Vetvy: `master` (prod) + `dev`.
- Checkout `~/devel/vyuctovanie` je PROD — timer beží z neho, musí stáť na
  `master`. Vývoj rob vo worktree `~/devel/vyuctovanie-dev` (branch `dev`),
  PR dev→master, po merge v prod checkoute `git pull` (= deploy pre všetkých naraz).
- CI (GitHub Actions): pytest + coverage gate + version-check; merge až so zelenou CI.
- Verzia: `vyuct/__init__.py` `__version__` — bump je PRVÝ commit na dev po každom merge.
- Zlyhaný beh alertuje cez `OnFailure=vyuctovanie-fail@%i.service` (Discord/journal).

## Playbook router

- odoo API → `.claude/rules/odoo-api.md` (auto-loads na vyuct/odoo.py, vyuct/config.py)
