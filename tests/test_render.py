"""Testy formátovania správ."""
from datetime import datetime
from zoneinfo import ZoneInfo

from vyuct.render import fmt_num, render

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
    # medzisúčty na osobu (hodiny aj €)
    assert '<b>Ján Novák</b> — 6 h × 10 €/h = <b>60 €</b>' in body
    assert '<b>Peter Kováč</b> — 2,5 h × 10 €/h = <b>25 €</b>' in body
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
    assert '<b>Marek</b> — 2 h × 10 €/h = <b>20 €</b>' in body


def test_render_settlement_per_person_rates(monkeypatch):
    from vyuct import config
    monkeypatch.setattr(config, 'RATES', {'Ján Novák': 15.0, 'Peter Kováč': 40.0})
    od = do = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    items = [(od, 'Ján Novák', 2.0, 'a'), (od, 'Peter Kováč', 3.0, 'b')]
    body = render(('settlement', 5.0, od, do, items))
    assert '<b>Ján Novák</b> — 2 h × 15 €/h = <b>30 €</b>' in body
    assert '<b>Peter Kováč</b> — 3 h × 40 €/h = <b>120 €</b>' in body
    assert 'Spolu odrobené: <b>5 h</b> = <b>150 €</b>' in body


def test_render_info_multi_author_detail(monkeypatch):
    from vyuct import config
    monkeypatch.setattr(config, 'RATES', {'Ján Novák': 15.0, 'Peter Kováč': 40.0})
    d = datetime(2026, 8, 12, 10, 0, tzinfo=TZ)
    body = render(('info', 5.0, [(d, 'Ján Novák', 2.0, ''), (d, 'Peter Kováč', 3.0, '')]))
    assert '5 h' in body and '150 €' in body
    assert 'Ján Novák 2 h = 30 €' in body
