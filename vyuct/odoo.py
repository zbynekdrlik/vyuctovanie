"""Odoo JSON-2 API klient."""
import json
import os
import urllib.error
import urllib.request

from .config import URL, DB, KEY_FILE, BOT_LOGIN


def api(path, payload, key):
    req = urllib.request.Request(
        f'{URL}/json/2/{path}', json.dumps(payload).encode(),
        {'Authorization': f'Bearer {key}', 'X-Odoo-Database': DB,
         'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:500]
        hint = ('; kľúč mohol expirovať (Odoo 19 obmedzuje platnosť na max 3 mesiace) — '
                'vygeneruj nový a nahraď obsah súboru s kľúčom' if e.code == 401 else '')
        raise SystemExit(f'Odoo API {path} zlyhalo: HTTP {e.code} — {detail}{hint}')
    except urllib.error.URLError as e:
        raise SystemExit(f'Odoo API {path} nedostupné: {e.reason}')
    except ValueError as e:
        raise SystemExit(f'Odoo API {path} vrátilo ne-JSON odpoveď: {e}')


def load_key():
    if not os.path.exists(KEY_FILE):
        raise SystemExit(f'Chýba API kľúč v {KEY_FILE}')
    if os.stat(KEY_FILE).st_mode & 0o077:
        raise SystemExit(f'{KEY_FILE} nesmie byť čitateľný pre skupinu/ostatných (chmod 600).')
    with open(KEY_FILE) as f:
        return f.read().strip()


def bot_partner_id(key):
    users = api('res.users/search_read',
                {'domain': [['login', '=', BOT_LOGIN]],
                 'fields': ['partner_id'], 'limit': 1}, key)
    if not users:
        raise SystemExit(f'Odoo používateľ {BOT_LOGIN} nenájdený.')
    return users[0]['partner_id'][0]


def fetch_messages(key, channel_id):
    """Všetky správy kanála (stránkovane, vzostupne podľa id)."""
    # Kanál má jednotky správ denne — celá história je lacná. Keby raz
    # narástla nad ~5000 správ, obmedziť fetch od poslednej uzávierky.
    out, offset, page = [], 0, 200
    while True:
        batch = api('mail.message/search_read',
                    {'domain': [['model', '=', 'discuss.channel'],
                                ['res_id', '=', channel_id]],
                     'fields': ['id', 'date', 'author_id', 'body'],
                     'limit': page, 'offset': offset, 'order': 'id asc'}, key)
        out.extend(batch)
        if len(batch) < page:
            return out
        offset += page


def post_message(key, channel_id, body_html):
    return api('discuss.channel/message_post',
               {'ids': [channel_id], 'body': body_html, 'body_is_html': True,
                'message_type': 'comment', 'subtype_xmlid': 'mail.mt_comment'}, key)
