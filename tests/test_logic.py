"""Testy rozhodovacej logiky — čo a kedy poslať."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from vyuct.logic import decide
from vyuct.parsing import enrich

TZ = ZoneInfo('Europe/Bratislava')
BOT = 1000
MAREK = [2000, 'Ján Novák']
ZBYNEK = [3000, 'Peter Kováč']


def mk(mid, body, author=None, date='2026-08-12 10:00:00'):
    return {'id': mid, 'body': body, 'author_id': author or MAREK, 'date': date}


def ts(h=20, m=5, d=17):
    return datetime(2026, 8, d, h, m, tzinfo=TZ)


def test_info_evening():
    msgs = enrich([mk(1, '- 4h praca'), mk(2, '- 2h ine', ZBYNEK)], BOT)
    actions = decide(msgs, ts(20, 5))
    assert len(actions) == 1
    assert actions[0][0] == 'info'
    assert actions[0][1] == 6


def test_info_not_before_20():
    msgs = enrich([mk(1, '- 4h praca')], BOT)
    assert decide(msgs, ts(19, 55)) == []


def test_info_once_per_day():
    msgs = enrich([
        mk(1, '- 4h praca'),
        mk(2, '<p>ℹ️ Priebežné info — od poslednej uzávierky odrobené: 4 h</p>',
           [BOT, 'Automatizacie'], '2026-08-17 17:30:00'),
    ], BOT)
    assert decide(msgs, ts(20, 5)) == []


def test_info_needs_new_hours_after_last_bot_msg():
    msgs = enrich([
        mk(1, '- 4h praca', MAREK, '2026-08-15 10:00:00'),
        mk(2, '<p>ℹ️ Priebežné info: 4 h</p>', [BOT, 'Automatizacie'], '2026-08-16 18:00:00'),
    ], BOT)
    assert decide(msgs, ts(20, 5)) == []


def test_info_new_hours_after_bot_reports_full_period_total():
    msgs = enrich([
        mk(1, '- 4h praca', MAREK, '2026-08-15 10:00:00'),
        mk(2, '<p>ℹ️ Priebežné info: 4 h</p>', [BOT, 'Automatizacie'], '2026-08-16 18:00:00'),
        mk(3, '- 2h dalsia praca', ZBYNEK, '2026-08-17 09:00:00'),
    ], BOT)
    actions = decide(msgs, ts(20, 5))
    assert len(actions) == 1
    assert actions[0][0] == 'info'
    assert actions[0][1] == 6


def test_settlement_on_uzavierka():
    msgs = enrich([mk(1, '- 4h praca'), mk(2, 'uzavierka', ZBYNEK)], BOT)
    actions = decide(msgs, ts(10, 0))
    assert len(actions) == 1
    assert actions[0][0] == 'settlement'
    assert actions[0][1] == 4


def test_settlement_not_duplicated():
    msgs = enrich([
        mk(1, '- 4h praca'),
        mk(2, 'uzavierka', ZBYNEK),
        mk(3, '<p>💰 VYÚČTOVANIE — obdobie</p>', [BOT, 'Automatizacie']),
    ], BOT)
    assert decide(msgs, ts(10, 0)) == []


def test_period_resets_after_uzavierka():
    msgs = enrich([
        mk(1, '- 4h stara praca'),
        mk(2, 'uzavierka', ZBYNEK),
        mk(3, '<p>💰 VYÚČTOVANIE — obdobie</p>', [BOT, 'Automatizacie']),
        mk(4, '- 2h nova praca'),
    ], BOT)
    actions = decide(msgs, ts(20, 5))
    assert len(actions) == 1
    assert actions[0][0] == 'info'
    assert actions[0][1] == 2


def test_second_settlement_counts_only_since_previous():
    msgs = enrich([
        mk(1, '- 4h stara praca'),
        mk(2, 'uzavierka', ZBYNEK),
        mk(3, '<p>💰 VYÚČTOVANIE — obdobie</p>', [BOT, 'Automatizacie']),
        mk(4, '- 2h nova praca'),
        mk(5, 'uzavierka', ZBYNEK),
    ], BOT)
    actions = decide(msgs, ts(10, 0))
    assert actions[0][0] == 'settlement'
    assert actions[0][1] == 2


def test_bot_messages_never_counted_as_hours():
    msgs = enrich([mk(1, '<p>29 h = 1450 €</p>', [BOT, 'Automatizacie'])], BOT)
    assert all(m['hours'] == 0 for m in msgs)
    assert decide(msgs, ts(20, 5)) == []


def test_force_info_ignores_window():
    msgs = enrich([mk(1, '- 4h praca')], BOT)
    actions = decide(msgs, ts(10, 0), force_info=True)
    assert len(actions) == 1
    assert actions[0][0] == 'info'
    assert actions[0][1] == 4


def test_force_info_zero_hours_sends_nothing():
    msgs = enrich([mk(1, 'Ďakujem')], BOT)
    assert decide(msgs, ts(10, 0), force_info=True) == []


def test_double_uzavierka_backlog_not_lost():
    msgs = enrich([
        mk(1, '- 5h praca'),
        mk(2, 'uzavierka', ZBYNEK),
        mk(3, 'uzavierka', ZBYNEK),
    ], BOT)
    actions = decide(msgs, ts(10, 0))
    assert actions[0][0] == 'settlement'
    assert actions[0][1] == 5


def test_settlement_carries_items_per_author():
    msgs = enrich([
        mk(1, '- 4h oprava webu', MAREK, '2026-08-12 10:00:00'),
        mk(2, '- 2h analýza', ZBYNEK, '2026-08-13 09:00:00'),
        mk(3, 'uzavierka', ZBYNEK, '2026-08-13 18:00:00'),
    ], BOT)
    actions = decide(msgs, ts(10, 0))
    assert len(actions) == 1
    _, total, od, do, items = actions[0]
    assert total == 6
    assert items == [
        (msgs[0]['date'], 'Ján Novák', 4.0, 'oprava webu'),
        (msgs[1]['date'], 'Peter Kováč', 2.0, 'analýza'),
    ]


def test_settlement_items_exclude_bot_messages():
    msgs = enrich([
        mk(1, '- 4h praca', MAREK, '2026-08-12 10:00:00'),
        mk(2, '<p>ℹ️ Priebežné info: 4 h</p>', [BOT, 'Automatizacie'], '2026-08-12 20:00:00'),
        mk(3, 'uzavierka', ZBYNEK, '2026-08-13 18:00:00'),
    ], BOT)
    actions = decide(msgs, ts(10, 0))
    _, total, od, do, items = actions[0]
    assert total == 4
    assert len(items) == 1
    assert items[0][1] == 'Ján Novák'


def test_double_uzavierka_settled_once():
    msgs = enrich([
        mk(1, '- 5h praca'),
        mk(2, 'uzavierka', ZBYNEK),
        mk(3, 'uzavierka', ZBYNEK),
        mk(4, '<p>💰 VYÚČTOVANIE — obdobie</p>', [BOT, 'Automatizacie']),
    ], BOT)
    assert decide(msgs, ts(10, 0)) == []


def test_decide_logs_reason_when_no_info(caplog):
    tz = ZoneInfo('Europe/Bratislava')
    msgs = [{'id': 1, 'uz': False, 'settlement': False, 'info': False,
             'hours': 2.0, 'is_bot': False, 'author': 'Ján Novák',
             'entries': [(2.0, '')],
             'date': datetime(2026, 8, 19, 10, 0, tzinfo=tz)}]
    with caplog.at_level(logging.INFO, logger='vyuctovanie'):
        actions = decide(msgs, datetime(2026, 8, 19, 10, 0, tzinfo=tz))
    assert actions == []
    assert any('info sa neposiela' in r.getMessage() for r in caplog.records)
