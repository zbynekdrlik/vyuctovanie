"""Testy extrakcie textu, hodín a klasifikácie správ."""
from vyuct.parsing import enrich, is_uzavierka, parse_entries, parse_hours, to_text

BOT = 1000
MAREK = [2000, 'Ján Novák']


def mk(mid, body, author=None, date='2026-08-12 10:00:00'):
    return {'id': mid, 'body': body, 'author_id': author or MAREK, 'date': date}


# ---------- parse_hours ----------

def test_parse_simple():
    assert parse_hours('- 4h\n- Nový návrhový výkres pergoly') == 4


def test_parse_with_topic():
    assert parse_hours('- 3h emali o zaplateni\n- Analýza, prečo nechodia e-maily') == 3


def test_parse_decimal_comma_and_dot():
    assert parse_hours('- 1,5h popis') == 1.5
    assert parse_hours('- 2.5h popis') == 2.5


def test_parse_multiple_lines_sum():
    assert parse_hours('- 2h projekt A\n- 3h projekt B') == 5


def test_parse_ignores_midline_range():
    assert parse_hours('- Oprava čaká na CI, behy trvajú 1-2 h') == 0


def test_parse_no_dash():
    assert parse_hours('2h parovanie pokladna zakazky') == 2


def test_parse_hod_suffix():
    assert parse_hours('- 3 hod upratovanie skladu') == 3


def test_parse_plain_text_no_hours():
    assert parse_hours('Ďakujem') == 0


def test_parse_hodiny_variants():
    assert parse_hours('- 3 hodiny upratovanie') == 3
    assert parse_hours('- 2 hodín skladu') == 2
    assert parse_hours('- 1 hodina navyse') == 1


def test_parse_html_list_items():
    assert parse_hours(to_text('<ul><li>- 4h A</li><li>- 2h B</li></ul>')) == 6


# ---------- parse_entries ----------

def test_parse_entries_with_description():
    assert parse_entries('- 4h oprava webu') == [(4.0, 'oprava webu')]


def test_parse_entries_hodiny_word_with_description():
    assert parse_entries('3 hodiny svadba') == [(3.0, 'svadba')]


def test_parse_entries_bare_no_description():
    assert parse_entries('- 2h') == [(2.0, '')]


def test_parse_entries_multiline_order():
    text = '- 2h projekt A\n- 3h projekt B'
    assert parse_entries(text) == [(2.0, 'projekt A'), (3.0, 'projekt B')]


def test_parse_entries_ignores_midline_range():
    assert parse_entries('- Oprava čaká na CI, behy trvajú 1-2 h') == []


# ---------- #16: popis z nasledujúcich riadkov, keď je hodinový riadok holý ----------

def test_parse_entries_bare_hour_line_takes_description_from_following_bullets():
    text = '- 4h\n- prvá vec, ktorá sa robila\n- druhá vec'
    assert parse_entries(text) == [(4.0, 'prvá vec, ktorá sa robila; druhá vec')]


def test_parse_entries_hour_line_with_description_ignores_following_bullets():
    text = '- 4h oprava webu\n- detail 1\n- detail 2'
    assert parse_entries(text) == [(4.0, 'oprava webu')]


def test_parse_entries_two_bare_hour_lines_each_get_own_continuation():
    text = '- 2h\ndetail A\n- 3h\ndetail B'
    assert parse_entries(text) == [(2.0, 'detail A'), (3.0, 'detail B')]


def test_parse_entries_bare_hour_line_followed_by_hour_line_with_description():
    text = '- 2h\n- 3h popis'
    assert parse_entries(text) == [(2.0, ''), (3.0, 'popis')]


def test_parse_entries_person_prefix_line_not_swallowed_as_description():
    text = 'Meno:\n- 4h\n- prvá vec\n- druhá vec'
    assert parse_entries(text) == [(4.0, 'prvá vec; druhá vec')]


def test_parse_entries_blank_line_inside_continuation_does_not_end_collection():
    text = '- 4h\n- prvá vec\n\n- druhá vec'
    assert parse_entries(text) == [(4.0, 'prvá vec; druhá vec')]


def test_parse_entries_continuation_collapses_internal_whitespace():
    text = '- 4h\n- prvá    vec  s  medzerami'
    assert parse_entries(text) == [(4.0, 'prvá vec s medzerami')]


def test_parse_entries_bare_hour_no_following_lines_stays_empty():
    assert parse_entries('- 2h') == [(2.0, '')]


# ---------- is_uzavierka ----------

def test_uzavierka_variants():
    assert is_uzavierka('uzavierka')
    assert is_uzavierka('Uzávierka')
    assert is_uzavierka(' uzávierka. ')
    assert not is_uzavierka('uzavierka bude zajtra')
    assert not is_uzavierka('- 4h')


# ---------- to_text ----------

def test_to_text_html():
    assert to_text('<p>- 4h</p><p>x &amp; y</p>') == '- 4h\nx & y'


# ---------- enrich ----------

def test_bot_messages_never_counted_as_hours():
    msgs = enrich([mk(1, '<p>29 h = 1450 €</p>', [BOT, 'Automatizacie'])], BOT)
    assert all(m['hours'] == 0 for m in msgs)
