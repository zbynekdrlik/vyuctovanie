"""Odoo JSON-2 API klient."""
import base64
import json
import logging
import os
import urllib.error
import urllib.request

from .config import URL, DB, KEY_FILE, BOT_LOGIN

log = logging.getLogger('vyuctovanie')

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


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


def create_attachment(key, name, data, mimetype=XLSX_MIME):
    """Vytvor ir.attachment z bytov (base64), vráť id novej prílohy.

    JSON-2 `create` berie `vals_list` (pole dictov) a vracia zoznam intov
    (overené naživo). ``data`` = surové bajty súboru.
    """
    res = api('ir.attachment/create',
              {'vals_list': [{'name': name,
                              'datas': base64.b64encode(data).decode(),
                              'mimetype': mimetype}]}, key)
    att_id = res[0] if isinstance(res, list) else res
    if isinstance(att_id, dict):  # obrana, keby server vrátil dict
        att_id = att_id.get('id')
    log.info('ir.attachment vytvorená: id=%s name=%s bytov=%d mime=%s',
             att_id, name, len(data), mimetype)
    return att_id


def post_message(key, channel_id, body_html, attachment_ids=None):
    payload = {'ids': [channel_id], 'body': body_html, 'body_is_html': True,
               'message_type': 'comment', 'subtype_xmlid': 'mail.mt_comment'}
    if attachment_ids:
        payload['attachment_ids'] = attachment_ids
    log.info('message_post → kanál=%s telo=%dB príloh=%d',
             channel_id, len(body_html), len(attachment_ids or []))
    return api('discuss.channel/message_post', payload, key)
