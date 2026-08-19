"""CLI vstupný bod."""
import argparse
import fcntl
import json
import logging
from datetime import datetime

from urllib.parse import urlparse

from .config import CHANNEL_ID, TZ, URL, validate
from .parsing import enrich
from .logic import decide
from .render import render, fmt_num
from .odoo import load_key, bot_partner_id, fetch_messages, post_message

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
        if args.dry_run:
            log.info('DRY-RUN, poslal by som: %s', body)
            continue
        result = post_message(key, args.channel, body)
        log.info('poslané (%s): %s → odpoveď: %s', a[0], body,
                 json.dumps(result, ensure_ascii=False)[:200])
    return 0
