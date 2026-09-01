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
    """Zoznam (hodiny, popis) zo všetkých riadkov tvaru „- 4h popis".

    Keď hodinový riadok nemá popis na tom istom riadku (napr. holé „- 4h"),
    popis sa doplní z NASLEDUJÚCICH neprázdnych riadkov správy — až po ďalší
    hodinový riadok alebo koniec správy (#16): každému sa odstráni vedúce
    „-"/„–" + whitespace, vnútorný whitespace sa skolabuje na jednu medzeru
    a jednotlivé riadky sa spoja cez „; ". Prázdne riadky sa preskakujú, ale
    zber neukončujú. Keď hodinový riadok popis MÁ, nasledujúce riadky sa
    ďalej ignorujú (nezmenené správanie) — continuation vždy patrí
    najbližšiemu predchádzajúcemu hodinovému riadku bez popisu.
    """
    out = []
    pending = None  # index poslednej pridanej položky čakajúcej na popis
    for line in text.splitlines():
        m = HOUR_RE.match(line)
        if m:
            desc = line[m.end():].strip(' \t-–—:;,.')
            out.append([float(m.group(1).replace(',', '.')), desc])
            pending = len(out) - 1 if not desc else None
            continue
        if pending is None:
            continue
        s = line.strip()
        if not s:
            continue
        piece = re.sub(r'\s+', ' ', s.lstrip('-–').strip())
        if not piece:
            continue
        existing = out[pending][1]
        out[pending][1] = f'{existing}; {piece}' if existing else piece
    return [(h, d) for h, d in out]


def parse_hours(text):
    """Súčet hodín zo všetkých riadkov tvaru „- 4h" / „1,5h popis"."""
    return sum(h for h, _ in parse_entries(text))


_NAME_PUNCT = frozenset("-.'")


def _looks_like_name(s):
    """``True`` ak ``s`` je HOLÉ MENO: 1–3 slová oddelené medzerami, každé
    slovo aspoň s jedným unicode písmenom a zložené LEN z písmen + ``-`` ``.``
    ``'`` (napr. ``Zora``, ``Anna-Mária``, ``Ján Novák ml.``).

    Sprísnenie #11: čokoľvek s číslicou, „—" medzi slovami, > 3 slovami či
    inou interpunkciou (nadpisový riadok „Prepis výkazu z aplikácie — Meno")
    → ``False``.
    """
    words = s.split()
    if not 1 <= len(words) <= 3:
        return False
    return all(
        any(ch.isalpha() for ch in w) and all(ch.isalpha() or ch in _NAME_PUNCT for ch in w)
        for w in words
    )


def parse_person(text):
    """Prefixové meno z prvého neprázdneho riadku „Meno:" (inak ``None``).

    Konvencia pre hodiny odpracované ZA niekoho, kto v kanáli sám nepíše (#9):
    zapisovateľ dá na prvý neprázdny riadok „Meno:" a všetky položky správy
    patria tomuto menu namiesto autora správy. O prefixe rozhoduje IBA prvý
    neprázdny riadok — ak NEmatchuje :data:`HOUR_RE`, má ≤ 40 znakov, nezačína
    „-", končí „:" A text pred „:" je HOLÉ MENO (:func:`_looks_like_name` —
    1–3 slová, len písmená/``-``/``.``/``'``), vráti meno (bez koncovej
    dvojbodky, orezané); inak ``None`` (aj keď niektorý neskorší riadok
    vyzerá ako „Meno:").

    Sprísnenie #11: nadpisový riadok „Prepis výkazu z aplikácie — Meno:"
    (viac slov, „—", číslice) NIE je meno → hodiny idú autorovi správy.
    """
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        # prvý NEPRÁZDNY riadok rozhoduje — buď je to „Meno:", alebo prefix nie je
        if (len(s) <= 40 and s.endswith(':')
                and not s.startswith('-') and not HOUR_RE.match(line)):
            candidate = s[:-1].strip()
            return candidate if _looks_like_name(candidate) else None
        return None
    return None


def is_uzavierka(text):
    """Správa, ktorej celý text je „uzavierka" (bez ohľadu na diakritiku/veľkosť)."""
    norm = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.fullmatch(r'\W*uzavierka\W*', norm, re.IGNORECASE) is not None


def enrich(messages, bot_partner_id):
    """Doplní každému message-dictu text, hodiny, položky a klasifikáciu.

    Pri ne-bot správe s prefixom „Meno:" na prvom riadku (:func:`parse_person`)
    idú všetky položky pod prefixové meno namiesto autora správy (#9). Bot
    správy sa neparsujú — nechávajú si meno bota.
    """
    out = []
    for m in sorted(messages, key=lambda x: x['id']):
        t = to_text(m['body'])
        author_pid = m['author_id'][0] if m.get('author_id') else None
        is_bot = author_pid == bot_partner_id
        entries = [] if is_bot else parse_entries(t)
        author = m['author_id'][1] if m.get('author_id') else '?'
        if not is_bot:
            author = parse_person(t) or author
        out.append({
            'id': m['id'],
            'date': datetime.strptime(m['date'], '%Y-%m-%d %H:%M:%S')
                    .replace(tzinfo=timezone.utc).astimezone(TZ),
            'author': author,
            'text': t,
            'is_bot': is_bot,
            'hours': sum(h for h, _ in entries),
            'entries': entries,
            'uz': (not is_bot) and is_uzavierka(t),
            'settlement': is_bot and SETTLEMENT_MARK in t,
            'info': is_bot and INFO_MARK in t,
        })
    return out
