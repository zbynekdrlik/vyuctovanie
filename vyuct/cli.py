"""CLI vstupný bod."""
import argparse
import fcntl
import json
import logging
import os
import tempfile
from datetime import datetime

from urllib.parse import urlparse

from .config import CHANNEL_ID, CLIENT_NAME, TZ, URL, validate
from .parsing import enrich
from .logic import decide
from .render import render, fmt_num
from .xlsx import build_xlsx, xlsx_filename
from .odoo import (load_key, bot_partner_id, fetch_messages, post_message,
                   create_attachment)

log = logging.getLogger('vyuctovanie')


def lock_path(url, channel):
    """Jeden lock na inštanciu (host+kanál) — rôzni zákazníci sa neblokujú."""
    host = urlparse(url).hostname or 'unknown'
    return f'/tmp/vyuctovanie-{host}-{channel}.lock'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true', help='len vypíš, nič neposielaj')
    ap.add_argument('--force-info', action='store_true',
                    help='pošli priebežné info hneď (ignoruje večerné okno aj denný limit)')
    ap.add_argument('--channel', type=int, default=CHANNEL_ID)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    validate(args.channel)

    lock = open(lock_path(URL, args.channel), 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.info('iný beh práve prebieha — končím.')
        return 0

    key = load_key()
    bot_pid = bot_partner_id(key)
    raw = fetch_messages(key, args.channel)
    msgs = enrich(raw, bot_pid)
    now = datetime.now(TZ)
    log.info('kanál %s: %d správ, bot partner %s, čas %s',
             args.channel, len(msgs), bot_pid, now.strftime('%H:%M'))

    hour_msgs = [m for m in msgs if m['hours'] > 0]
    log.info('hodinových správ spolu: %d (%s h); uzávierok: %d; bot reportov: %d',
             len(hour_msgs), fmt_num(sum(m['hours'] for m in hour_msgs)),
             sum(1 for m in msgs if m['uz']),
             sum(1 for m in msgs if m['settlement'] or m['info']))

    actions = decide(msgs, now, force_info=args.force_info)
    if not actions:
        log.info('nič na poslanie.')
        return 0

    for a in actions:
        body = render(a)
        # XLSX prílohu dostane LEN vyúčtovanie (info nie).
        xlsx_bytes = fname = None
        if a[0] == 'settlement':
            _, _total, od, do, items = a
            xlsx_bytes = build_xlsx(od, do, items, CLIENT_NAME)
            fname = xlsx_filename(od, do, CLIENT_NAME)
            log.info('XLSX vygenerovaný: %s (%d položiek, %d bajtov)',
                     fname, len(items), len(xlsx_bytes))
        if args.dry_run:
            if xlsx_bytes:
                # Súkromný dočasný adresár (mode 0700) — bezpečné voči
                # symlink-clobberu na viacpoužívateľskom stroji, no s
                # čitateľným názvom súboru pre kontrolu.
                path = os.path.join(tempfile.mkdtemp(prefix='vyuct-'), fname)
                with open(path, 'wb') as fh:
                    fh.write(xlsx_bytes)
                log.info('DRY-RUN, XLSX uložený do: %s (%d bajtov)', path, len(xlsx_bytes))
            log.info('DRY-RUN, poslal by som: %s', body)
            continue
        attachment_ids = None
        if xlsx_bytes:
            attachment_ids = [create_attachment(key, fname, xlsx_bytes)]
        try:
            result = post_message(key, args.channel, body, attachment_ids)
        except Exception:
            # Ak sa príloha vytvorila, ale post zlyhal, ostáva na serveri
            # osirelá ir.attachment (bez res_model/res_id) — zaloguj jej id,
            # nech je dohľadateľná (settlement je idempotentný, ďalší beh
            # sa prepočíta z histórie).
            if attachment_ids:
                log.error('post_message zlyhal — osirelá ir.attachment id=%s (name=%s)',
                          attachment_ids[0], fname)
            raise
        log.info('poslané (%s, príloh=%d): %s → odpoveď: %s', a[0],
                 len(attachment_ids or []), body,
                 json.dumps(result, ensure_ascii=False)[:200])
    return 0
