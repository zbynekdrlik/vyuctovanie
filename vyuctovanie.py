#!/usr/bin/env python3
"""Vyúčtovanie hodín z Odoo Discuss kanála výkazov (multi-zákaznícke).

Číta správy kanála, extrahuje odrobené hodiny (riadky tvaru „- 4h", „- 1,5h popis"),
a posiela do TOHO ISTÉHO kanála:

  * VYÚČTOVANIE — hneď po správe „uzavierka": súčet hodín od predošlej uzávierky.
    Od tej chvíle sa počíta odznova (rátajú sa len správy za uzávierkou).
  * Priebežné info — o 20:00 (okno 20:00–20:59; hodiny zapísané po 20:59 idú do
    infa nasledujúci deň), ak od posledného reportu pribudli nové hodiny:
    priebežný súčet od poslednej uzávierky. Max 1× denne.

Stav sa NEuchováva lokálne — všetko sa odvodzuje z histórie kanála (posledná
uzávierka + posledné správy bota), takže behy sú idempotentné a nič sa nezdvojí.

Beží každých 10 minút cez systemd user template timer — jedna inštancia na
zákazníka (vyuctovanie@<meno>.timer), config v ~/.config/vyuct/<meno>.env.

API kľúč: cesta v ODOO_KEY_FILE (mode 600, MIMO git — nikdy ho
nekopíruj do repozitára, commitu ani do chatu). Používateľ „Automatizacie".

Použitie:
    python3 vyuctovanie.py               # ostrý beh (rozhodne a prípadne pošle)
    python3 vyuctovanie.py --dry-run     # len vypíše, čo by urobil
    python3 vyuctovanie.py --force-info  # pošle priebežné info hneď (ignoruje okno aj denný limit)
"""
import sys

from vyuct.cli import main

if __name__ == '__main__':
    sys.exit(main())
