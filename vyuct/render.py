"""Formátovanie správ."""
import html

from .config import SETTLEMENT_MARK, INFO_MARK, rate_for


def fmt_num(x):
    """29.0 → „29", 1.5 → „1,5" (slovenská desatinná čiarka)."""
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def _entry(date, hours, desc):
    txt = f' — {html.escape(desc)}' if desc else ''
    return f'<li>{date:%d.%m.} <b>{fmt_num(hours)} h</b>{txt}</li>'


def _person_block(author, entries):
    """Blok jedného človeka: medzisúčet v h aj € (jeho sadzbou) + zoznam položiek."""
    subtotal = sum(h for _, h, _ in entries)
    rate = rate_for(author)
    rows = ''.join(_entry(*e) for e in entries)
    return (f'<p><b>{html.escape(author)}</b> — {fmt_num(subtotal)} h × {fmt_num(rate)} €/h'
            f' = <b>{fmt_num(subtotal * rate)} €</b></p>'
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
        return (f'<p><b>💰 {SETTLEMENT_MARK}</b> — obdobie {od:%d.%m.%Y} → {do:%d.%m.%Y}</p>'
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
            f'{html.escape(a)} {fmt_num(h)} h = {fmt_num(h * rate_for(a))} €'
            for a, h in per.items()) + ')'
    return (f'<p><b>ℹ️ {INFO_MARK}</b> — od poslednej uzávierky odrobené:'
            f' <b>{fmt_num(total)} h</b> = <b>{fmt_num(eur)} €</b>{detail}</p>')
