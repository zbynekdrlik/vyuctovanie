"""Formátovanie správ."""
import html

from .config import SETTLEMENT_MARK, INFO_MARK, rate_for

_MONTHS_SK = (
    'január', 'február', 'marec', 'apríl', 'máj', 'jún',
    'júl', 'august', 'september', 'október', 'november', 'december',
)


def fmt_num(x):
    """29.0 → „29", 1.5 → „1,5" (slovenská desatinná čiarka)."""
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def period_label(items, od, do):
    """Obdobie vyúčtovania ako čitateľný popisok (#23).

    Keď ``items`` nie je prázdne a VŠETKY položky padnú do jedného kalendárneho
    mesiaca (rovnaký rok aj mesiac) → ``"<mesiac> <rok>"`` (napr. „august 2026").
    Inak (položky vo viacerých mesiacoch, alebo prázdne items) → doterajší
    rozsah dátumov ``od → do`` (uzávierka predošlá → aktuálna).

    Rozhodujú dátumy POLOŽIEK, nie hranice ``od``/``do`` — ``do`` je typicky
    1. deň nasledujúceho mesiaca (dátum uzávierky), takže rozsah uzávierka→
    uzávierka formálne vždy prechádza cez prelom mesiaca.
    """
    if items:
        first = items[0][0]
        year, month = first.year, first.month
        if all(date.year == year and date.month == month for date, *_ in items):
            return f'{_MONTHS_SK[month - 1]} {year}'
    return f'{od:%d.%m.%Y} → {do:%d.%m.%Y}'


def _entry(date, hours, desc):
    txt = f' — {html.escape(desc)}' if desc else ''
    return f'<li>{date:%d.%m.} <b>{fmt_num(hours)} h</b>{txt}</li>'


def _person_block(author, entries):
    """Blok jedného človeka: medzisúčet LEN v hodinách + zoznam položiek.

    Pri osobe sa sadzba ani € nezobrazuje (variant A, #7); celkové € sa ráta
    len v celkovom súčte cez ``rate_for`` v :func:`render`.
    """
    subtotal = sum(h for _, h, _ in entries)
    rows = ''.join(_entry(*e) for e in entries)
    return (f'<p><b>{html.escape(author)}</b> — {fmt_num(subtotal)} h</p>'
            f'<ul>{rows}</ul>')


def render(action):
    """Akcia → HTML telo správy."""
    if action[0] == 'settlement':
        _, total, od, do, items = action
        by_author = {}  # dict drží poradie prvého výskytu autora
        for date, author, hours, desc in items:
            by_author.setdefault(author, []).append((date, hours, desc))
        blocks = ''.join(_person_block(a, e) for a, e in by_author.items())
        eur = sum(sum(h for _, h, _ in e) * rate_for(a) for a, e in by_author.items())
        label = period_label(items, od, do)
        return (f'<p><b>💰 {SETTLEMENT_MARK}</b> — obdobie {label}</p>'
                f'{blocks}'
                f'<p>Spolu odrobené: <b>{fmt_num(total)} h</b> = <b>{fmt_num(eur)} €</b></p>'
                f'<p>Počítadlo začína odznova — rátajú sa správy za uzávierkou.</p>')
    _, total, items = action
    per = {}  # autor → hodiny, v poradí prvého výskytu
    for _, author, h, _ in items:
        per[author] = per.get(author, 0.0) + h
    eur = sum(h * rate_for(a) for a, h in per.items())
    detail = ''
    if len(per) > 1:
        detail = ' (' + '; '.join(
            f'{html.escape(a)} {fmt_num(h)} h'
            for a, h in per.items()) + ')'
    return (f'<p><b>ℹ️ {INFO_MARK}</b> — od poslednej uzávierky odrobené:'
            f' <b>{fmt_num(total)} h</b> = <b>{fmt_num(eur)} €</b>{detail}</p>')
