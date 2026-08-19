"""Formátovanie správ."""
import html

from .config import RATE_EUR, SETTLEMENT_MARK, INFO_MARK


def fmt_num(x):
    """29.0 → „29", 1.5 → „1,5" (slovenská desatinná čiarka)."""
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def _entry(date, hours, desc):
    txt = f' — {html.escape(desc)}' if desc else ''
    return f'<li>{date:%d.%m.} <b>{fmt_num(hours)} h</b>{txt}</li>'


def _person_block(author, entries):
    """Blok jedného človeka: medzisúčet v h aj € + zoznam jeho položiek."""
    subtotal = sum(h for _, h, _ in entries)
    rows = ''.join(_entry(*e) for e in entries)
    return (f'<p><b>{html.escape(author)}</b> — {fmt_num(subtotal)} h'
            f' = <b>{fmt_num(subtotal * RATE_EUR)} €</b></p>'
            f'<ul>{rows}</ul>')


def render(action):
    """Akcia → HTML telo správy."""
    if action[0] == 'settlement':
        _, total, od, do, items = action
        by_author = {}  # dict drží poradie prvého výskytu autora
        for date, author, hours, desc in items:
            by_author.setdefault(author, []).append((date, hours, desc))
        blocks = ''.join(_person_block(a, e) for a, e in by_author.items())
        return (f'<p><b>💰 {SETTLEMENT_MARK}</b> — obdobie {od:%d.%m.%Y} → {do:%d.%m.%Y}</p>'
                f'{blocks}'
                f'<p>Spolu odrobené: <b>{fmt_num(total)} h</b> = <b>{fmt_num(total * RATE_EUR)} €</b>'
                f' (sadzba {fmt_num(RATE_EUR)} €/h)</p>'
                f'<p>Počítadlo začína odznova — rátajú sa správy za uzávierkou.</p>')
    _, total = action
    eur = total * RATE_EUR
    return (f'<p><b>ℹ️ {INFO_MARK}</b> — od poslednej uzávierky odrobené:'
            f' <b>{fmt_num(total)} h</b> = <b>{fmt_num(eur)} €</b>'
            f' (sadzba {fmt_num(RATE_EUR)} €/h)</p>')
