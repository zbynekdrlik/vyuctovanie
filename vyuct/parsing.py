"""Extrakcia textu, hodín a klasifikácia správ."""
import html
import re
import unicodedata
from datetime import datetime, timezone

from .config import TZ, SETTLEMENT_MARK, INFO_MARK

HOUR_RE = re.compile(r'^\s*-?\s*(\d+(?:[.,]\d+)?)\s*h(?:od(?:in(?:a|y)?|ín)?)?\b',
                     re.MULTILINE | re.IGNORECASE)


def to_text(body):
    """HTML telo správy → čitateľný text so zachovanými riadkami."""
    body = re.sub(r'<br\s*/?>|</p>|</div>|</li>|</tr>|</h[1-6]>', '\n', body or '')
    return html.unescape(re.sub(r'<[^>]+>', '', body)).strip()


def parse_entries(text):
    """Zoznam (hodiny, popis) zo všetkých riadkov tvaru „- 4h popis"."""
    out = []
    for line in text.splitlines():
        m = HOUR_RE.match(line)
        if m:
            out.append((float(m.group(1).replace(',', '.')),
                        line[m.end():].strip(' \t-–—:;,.')))
    return out


def parse_hours(text):
    """Súčet hodín zo všetkých riadkov tvaru „- 4h" / „1,5h popis"."""
    return sum(h for h, _ in parse_entries(text))


def is_uzavierka(text):
    """Správa, ktorej celý text je „uzavierka" (bez ohľadu na diakritiku/veľkosť)."""
    norm = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.fullmatch(r'\W*uzavierka\W*', norm, re.IGNORECASE) is not None


def enrich(messages, bot_partner_id):
    """Doplní každému message-dictu text, hodiny, položky a klasifikáciu."""
    out = []
    for m in sorted(messages, key=lambda x: x['id']):
        t = to_text(m['body'])
        author = m['author_id'][0] if m.get('author_id') else None
        is_bot = author == bot_partner_id
        entries = [] if is_bot else parse_entries(t)
        out.append({
            'id': m['id'],
            'date': datetime.strptime(m['date'], '%Y-%m-%d %H:%M:%S')
                    .replace(tzinfo=timezone.utc).astimezone(TZ),
            'author': m['author_id'][1] if m.get('author_id') else '?',
            'text': t,
            'is_bot': is_bot,
            'hours': sum(h for h, _ in entries),
            'entries': entries,
            'uz': (not is_bot) and is_uzavierka(t),
            'settlement': is_bot and SETTLEMENT_MARK in t,
            'info': is_bot and INFO_MARK in t,
        })
    return out
