---
paths:
  - "vyuct/odoo.py"
  - "vyuct/config.py"
---

# Odoo JSON-2 API — gotchas

- `POST /json/2/{model}/{method}`, hlavičky `Authorization: Bearer <key>` + `X-Odoo-Database: <db>`. Kľúč číta appka zo súboru v `ODOO_KEY_FILE` (mode 600, MIMO git). Odoo 19: kľúče platia max 3 mesiace.
- `discuss.channel/message_post` vracia **403 pre ne-člena kanála** — aj keď ten istý user správy kanála prečíta (čítanie má vyššie práva, zápis chce členstvo). Fix: pozvať bot usera do kanála, nie meniť kľúč.
- `body_is_html: true` povinné pri HTML tele — inak Odoo tagy escapne.
- `mail.message/search_read`: `order: 'id asc'` + stránkovanie po 200, inak limit ticho oreže históriu.
- `message_post` berie `author_id: <partner_id>` — bot môže poslať správu POD MENOM iného partnera (overené live). Takto poslané hodiny appka POČÍTA (autor ≠ bot partner) a v rozpise idú pod správne meno.
- Práva bota na mazanie: `mail.message/unlink` FUNGUJE aj na cudziu správu, ale `discuss.channel/unlink` vracia `AccessError` (mazanie kanálov je admin-only). Testovací kanál preto po sebe nezmažeš — nevyrábaj ho, alebo ho nechaj zmazať usera v UI.
