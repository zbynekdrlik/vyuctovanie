"""Testy formátovania správ."""
from datetime import datetime
from zoneinfo import ZoneInfo

from vyuct.render import fmt_num, period_label, render

TZ = ZoneInfo('Europe/Bratislava')


def test_fmt_num():
    assert fmt_num(29.0) == '29'
    assert fmt_num(1.5) == '1,5'
    assert fmt_num(1450.0) == '1450'


def test_render_info():
    d = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    body = render(('info', 29.0, [(d, 'Ján Novák', 29.0, '')]))
    assert '29 h' in body
    assert '290 €' in body
    assert 'Priebežné info' in body
    assert 'Ján Novák' not in body


def test_render_settlement():
    od = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    do = datetime(2026, 8, 12, 18, 0, tzinfo=TZ)
    body = render(('settlement', 4.0, od, do, []))
    assert 'VYÚČTOVANIE' in body
    assert '12.08.2026' in body


def test_render_settlement_no_items_has_no_list():
    od = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    do = datetime(2026, 8, 12, 18, 0, tzinfo=TZ)
    body = render(('settlement', 4.0, od, do, []))
    assert '<ul>' not in body


def test_render_settlement_groups_by_person_with_subtotals():
    od = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    do = datetime(2026, 8, 13, 18, 0, tzinfo=TZ)
    items = [
        (datetime(2026, 8, 12, 10, 0, tzinfo=TZ), 'Ján Novák', 4.0, 'oprava webu'),
        (datetime(2026, 8, 13, 9, 0, tzinfo=TZ), 'Peter Kováč', 2.5, 'analýza'),
        (datetime(2026, 8, 13, 14, 0, tzinfo=TZ), 'Ján Novák', 2.0, 'deploy'),
    ]
    body = render(('settlement', 8.5, od, do, items))
    assert body.count('<li>') == 3
    # medzisúčty na osobu LEN v hodinách — žiadna sadzba, žiadne € (variant A, #7)
    assert '<p><b>Ján Novák</b> — 6 h</p>' in body
    assert '<p><b>Peter Kováč</b> — 2,5 h</p>' in body
    # pri osobe sa sadzba ani € nezobrazuje
    assert '€/h' not in body
    assert '×' not in body
    # položky bez opakovania mena (meno je v hlavičke bloku)
    assert '<li>12.08. <b>4 h</b> — oprava webu</li>' in body
    assert '<li>13.08. <b>2,5 h</b> — analýza</li>' in body
    assert '<li>13.08. <b>2 h</b> — deploy</li>' in body
    # celkový súčet
    assert 'Spolu odrobené: <b>8,5 h</b> = <b>85 €</b>' in body
    # poradie osôb = poradie prvého výskytu
    assert body.index('Ján Novák') < body.index('Peter Kováč')


def test_render_settlement_escapes_html_in_author_and_description():
    od = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    do = datetime(2026, 8, 12, 18, 0, tzinfo=TZ)
    items = [(od, '<i>Marek</i>', 1.0, '<b>&</b> test')]
    body = render(('settlement', 1.0, od, do, items))
    assert '&lt;b&gt;&amp;&lt;/b&gt; test' in body
    assert '&lt;i&gt;Marek&lt;/i&gt;' in body
    # no raw tags leaked from user content (only the ones we render ourselves)
    assert '<b>&</b>' not in body
    assert '<i>Marek</i>' not in body


def test_render_settlement_bare_hours_no_description():
    od = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    do = datetime(2026, 8, 12, 18, 0, tzinfo=TZ)
    items = [(od, 'Marek', 2.0, '')]
    body = render(('settlement', 2.0, od, do, items))
    assert '<li>12.08. <b>2 h</b></li>' in body
    assert '<p><b>Marek</b> — 2 h</p>' in body
    # pri osobe žiadna sadzba/€ (celkový total s € ostáva)
    assert '€/h' not in body
    assert '×' not in body


def test_render_settlement_per_person_rates(monkeypatch):
    from vyuct import config
    monkeypatch.setattr(config, 'RATES', {'Ján Novák': 15.0, 'Peter Kováč': 40.0})
    od = do = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    items = [(od, 'Ján Novák', 2.0, 'a'), (od, 'Peter Kováč', 3.0, 'b')]
    body = render(('settlement', 5.0, od, do, items))
    # pri osobe len hodiny (žiadna sadzba), ale celkový total ráta per-osoba sadzby
    assert '<p><b>Ján Novák</b> — 2 h</p>' in body
    assert '<p><b>Peter Kováč</b> — 3 h</p>' in body
    assert '€/h' not in body
    assert '×' not in body
    # per-osoba € (30 €, 120 €) sa NEzobrazuje, len celkový súčet
    assert '30 €' not in body
    assert '120 €' not in body
    # celkový súčet naďalej používa per-osoba sadzby: 2 h @15 + 3 h @40 = 150 €
    assert 'Spolu odrobené: <b>5 h</b> = <b>150 €</b>' in body


def test_render_info_multi_author_detail(monkeypatch):
    from vyuct import config
    monkeypatch.setattr(config, 'RATES', {'Ján Novák': 15.0, 'Peter Kováč': 40.0})
    d = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    body = render(('info', 5.0, [(d, 'Ján Novák', 2.0, ''), (d, 'Peter Kováč', 3.0, '')]))
    # celkový súčet ostáva v h aj € (per-osoba sadzby: 2 h @15 + 3 h @40 = 150 €)
    assert '5 h' in body and '150 €' in body
    # detail pri osobách LEN v hodinách — žiadne € (variant A, #7)
    assert '(Ján Novák 2 h; Peter Kováč 3 h)' in body
    assert '30 €' not in body
    assert '120 €' not in body


# --- period_label + jeho použitie v render() (#23) ---------------------

def test_period_label_single_month_returns_month_name_and_year():
    items = [
        (datetime(2026, 8, 12, 10, 0, tzinfo=TZ), 'Ján Novák', 4.0, 'oprava'),
        (datetime(2026, 8, 30, 9, 0, tzinfo=TZ), 'Peter Kováč', 2.0, 'analýza'),
    ]
    od = datetime(2026, 8, 1, 0, 0, tzinfo=TZ)
    do = datetime(2026, 9, 1, 0, 0, tzinfo=TZ)
    assert period_label(items, od, do) == 'august 2026'


def test_period_label_february_uses_diacritic_month_name():
    items = [(datetime(2026, 2, 5, 9, 0, tzinfo=TZ), 'Marek', 1.0, '')]
    od = datetime(2026, 2, 1, 0, 0, tzinfo=TZ)
    do = datetime(2026, 3, 1, 0, 0, tzinfo=TZ)
    assert period_label(items, od, do) == 'február 2026'


def test_period_label_multi_month_items_fall_back_to_date_range():
    items = [
        (datetime(2026, 8, 30, 10, 0, tzinfo=TZ), 'Ján Novák', 4.0, 'oprava'),
        (datetime(2026, 9, 1, 9, 0, tzinfo=TZ), 'Peter Kováč', 2.0, 'analýza'),
    ]
    od = datetime(2026, 8, 12, 0, 0, tzinfo=TZ)
    do = datetime(2026, 9, 1, 8, 0, tzinfo=TZ)
    assert period_label(items, od, do) == '12.08.2026 → 01.09.2026'


def test_period_label_empty_items_fall_back_to_date_range():
    od = datetime(2026, 8, 12, 0, 0, tzinfo=TZ)
    do = datetime(2026, 9, 1, 8, 0, tzinfo=TZ)
    assert period_label([], od, do) == '12.08.2026 → 01.09.2026'


def test_period_label_same_month_number_different_year_not_merged():
    items = [
        (datetime(2025, 8, 30, tzinfo=TZ), 'Ján Novák', 1.0, ''),
        (datetime(2026, 8, 1, tzinfo=TZ), 'Peter Kováč', 2.0, ''),
    ]
    od = datetime(2025, 8, 12, 0, 0, tzinfo=TZ)
    do = datetime(2026, 8, 1, 0, 0, tzinfo=TZ)
    assert period_label(items, od, do) == '12.08.2025 → 01.08.2026'


def test_render_settlement_uses_month_label_when_items_span_one_month():
    od = datetime(2026, 8, 12, 0, 0, tzinfo=TZ)
    do = datetime(2026, 9, 1, 8, 0, tzinfo=TZ)
    items = [
        (datetime(2026, 8, 12, 10, 0, tzinfo=TZ), 'Ján Novák', 4.0, 'oprava'),
        (datetime(2026, 8, 20, 9, 0, tzinfo=TZ), 'Peter Kováč', 2.0, 'analýza'),
    ]
    body = render(('settlement', 6.0, od, do, items))
    assert 'obdobie august 2026' in body
    assert '→' not in body


def test_render_settlement_uses_date_range_when_items_span_two_months():
    od = datetime(2026, 8, 12, 0, 0, tzinfo=TZ)
    do = datetime(2026, 9, 1, 8, 0, tzinfo=TZ)
    items = [
        (datetime(2026, 8, 30, 10, 0, tzinfo=TZ), 'Ján Novák', 4.0, 'oprava'),
        (datetime(2026, 9, 1, 7, 0, tzinfo=TZ), 'Peter Kováč', 2.0, 'analýza'),
    ]
    body = render(('settlement', 6.0, od, do, items))
    assert 'obdobie 12.08.2026 → 01.09.2026' in body
