"""Testy prefixu „Meno:" na prvom riadku správy — hodiny za iného človeka (#9).

Konvencia: zapisovateľ zapíše hodiny ZA niekoho, kto v kanáli sám nepíše, tak, že
prvý neprázdny riadok správy je „Meno:". Všetky položky správy potom patria tomu
menu namiesto autora správy. Mená v testoch sú čisto fiktívne.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from vyuct.logic import decide
from vyuct.parsing import enrich
from vyuct.render import render

TZ = ZoneInfo('Europe/Bratislava')
BOT = 1000
WRITER = [2000, 'Ján Novák']      # zapisovateľ = autor správy
AUTHOR_B = [3000, 'Peter Kováč']


def mk(mid, body, author=None, date='2026-08-12 10:00:00'):
    return {'id': mid, 'body': body, 'author_id': author or WRITER, 'date': date}


def ts(h=20, m=5, d=17):
    return datetime(2026, 8, d, h, m, tzinfo=TZ)


# ---------- parse_person ----------

def test_parse_person_prefix_first_line():
    from vyuct.parsing import parse_person
    assert parse_person('Oľga Testová:\n- 6h návrh výkresu') == 'Oľga Testová'


def test_parse_person_strips_colon_and_whitespace():
    from vyuct.parsing import parse_person
    assert parse_person('Braňo Malý:  \n- 3h skladu') == 'Braňo Malý'


def test_parse_person_skips_leading_blank_lines():
    from vyuct.parsing import parse_person
    assert parse_person('\n\nOľga Testová:\n- 2h') == 'Oľga Testová'


def test_parse_person_no_prefix_when_first_line_is_hours():
    from vyuct.parsing import parse_person
    assert parse_person('- 4h praca') is None


def test_parse_person_hours_line_with_colon_not_name():
    # riadok hodín končiaci dvojbodkou sa NESMIE chytiť ako meno
    from vyuct.parsing import parse_person
    assert parse_person('- 4h popis:') is None


def test_parse_person_plain_line_without_colon_is_none():
    from vyuct.parsing import parse_person
    assert parse_person('Ďakujem\n- 4h praca') is None


def test_parse_person_over_40_chars_is_not_name():
    # 41 znakov (meno 40 + „:") je nad hranicou → None
    from vyuct.parsing import parse_person
    assert parse_person('X' * 40 + ':\n- 2h') is None


def test_parse_person_exactly_40_chars_is_name():
    # 40 znakov (meno 39 + „:") je presne na hranici (≤ 40) → meno
    from vyuct.parsing import parse_person
    assert parse_person('X' * 39 + ':\n- 2h') == 'X' * 39


def test_parse_person_hyphenated_name():
    # meno s pomlčkou VNÚTRI (nezačína „-") je platné meno
    from vyuct.parsing import parse_person
    assert parse_person('Anna-Mária:\n- 2h') == 'Anna-Mária'


def test_parse_person_colon_only_line_is_none():
    # samotná „:" (aj s medzerami) nie je meno — kontrakt meno-alebo-None
    from vyuct.parsing import parse_person
    assert parse_person(':\n- 2h') is None
    assert parse_person('   :   \n- 2h') is None


def test_parse_person_only_first_nonempty_line_decides():
    # prefix musí byť PRVÝ neprázdny riadok; neskorší „Meno:" sa neberie
    from vyuct.parsing import parse_person
    assert parse_person('- 4h praca\nOľga Testová:') is None


def test_parse_person_empty_text_is_none():
    from vyuct.parsing import parse_person
    assert parse_person('') is None
    assert parse_person('\n  \n') is None


# ---------- enrich ----------

def test_enrich_prefix_assigns_items_to_prefix_name():
    # správu napísal „Ján Novák", prefix je „Oľga Testová:" → hodiny patria Oľge
    msgs = enrich([mk(1, '<p>Oľga Testová:</p><p>- 6h návrh výkresu</p>')], BOT)
    assert msgs[0]['author'] == 'Oľga Testová'
    assert msgs[0]['entries'] == [(6.0, 'návrh výkresu')]
    assert msgs[0]['hours'] == 6


def test_enrich_no_prefix_keeps_message_author():
    msgs = enrich([mk(1, '<p>- 4h praca</p>')], BOT)   # autor WRITER = Ján Novák
    assert msgs[0]['author'] == 'Ján Novák'


def test_enrich_bot_message_never_gets_prefix():
    # bot správa sa neparsuje na prefix, aj keby vyzerala ako „Meno:"
    msgs = enrich([mk(1, '<p>Niekto:</p><p>x</p>', [BOT, 'Automatizacie'])], BOT)
    assert msgs[0]['author'] == 'Automatizacie'


# ---------- decide + render (integrácia) ----------

def test_settlement_groups_and_bills_under_prefix_name(monkeypatch):
    from vyuct import config
    monkeypatch.setattr(config, 'RATES', {'Oľga Testová': 20.0, 'Ján Novák': 15.0})
    msgs = enrich([
        mk(1, '<p>Oľga Testová:</p><p>- 6h výkres</p>', WRITER, '2026-08-12 10:00:00'),
        mk(2, 'uzavierka', AUTHOR_B, '2026-08-12 18:00:00'),
    ], BOT)
    actions = decide(msgs, ts(10, 0))
    assert len(actions) == 1
    _, total, od, do, items = actions[0]
    assert total == 6
    assert items[0][1] == 'Oľga Testová'               # položka nesie prefixové meno
    body = render(actions[0])
    assert '<p><b>Oľga Testová</b> — 6 h</p>' in body   # medzisúčet pod prefixom
    # celkové € ráta sadzbu prefixového mena (Oľga 20 €/h), nie zapisovateľa (Ján 15)
    assert 'Spolu odrobené: <b>6 h</b> = <b>120 €</b>' in body


def test_info_bills_under_prefix_name_rate(monkeypatch):
    from vyuct import config
    monkeypatch.setattr(config, 'RATES', {'Oľga Testová': 20.0, 'Ján Novák': 15.0})
    msgs = enrich([mk(1, '<p>Oľga Testová:</p><p>- 6h výkres</p>', WRITER)], BOT)
    actions = decide(msgs, ts(20, 5))
    assert len(actions) == 1 and actions[0][0] == 'info'
    body = render(actions[0])
    # sadzba prefixového mena: 6 h @ 20 €/h = 120 € (nie 6 @ 15 = 90)
    assert '6 h' in body and '120 €' in body


# ---------- #11: prefix musí byť HOLÉ MENO (1–3 slová), nie nadpisový riadok ----------

def test_parse_person_multiword_heading_with_emdash_is_not_name():
    # regresia #11: nadpisový riadok „... — Meno:" NIE je meno → None (hodiny autorovi)
    from vyuct.parsing import parse_person
    assert parse_person('Prepis výkazu z aplikácie — Zora:\n- 3h návrh') is None


def test_parse_person_emdash_between_two_words_is_not_name():
    # „—" (pomlčka) medzi slovami → nie je meno
    from vyuct.parsing import parse_person
    assert parse_person('Meno — Priezvisko:\n- 2h') is None


def test_parse_person_line_with_digit_is_not_name():
    from vyuct.parsing import parse_person
    assert parse_person('Faktúra 2024:\n- 2h') is None


def test_parse_person_more_than_three_words_is_not_name():
    from vyuct.parsing import parse_person
    assert parse_person('Toto je dlhší nadpis:\n- 2h') is None


def test_parse_person_single_word_name_still_works():
    # holé jednoslovné meno ostáva menom (feature #9 nesmie prestať fungovať)
    from vyuct.parsing import parse_person
    assert parse_person('Zora:\n- 6h') == 'Zora'


def test_parse_person_three_word_name_with_dot_still_works():
    from vyuct.parsing import parse_person
    assert parse_person('Ján Novák ml.:\n- 6h') == 'Ján Novák ml.'


def test_parse_person_apostrophe_name_still_works():
    from vyuct.parsing import parse_person
    assert parse_person("O'Brien:\n- 6h") == "O'Brien"


def test_enrich_heading_prefix_falls_back_to_author():
    # #11: viacslovný nadpis s „—" sa NESMIE stať falošnou osobou —
    # všetky hodiny idú autorovi správy (ako pred #9)
    msgs = enrich([mk(
        1, '<p>Prepis výkazu z aplikácie — Zora:</p><p>- 3h návrh</p><p>- 4h montáž</p>',
        WRITER)], BOT)
    assert msgs[0]['author'] == 'Ján Novák'   # autor správy, nie nadpis
    assert msgs[0]['hours'] == 7
