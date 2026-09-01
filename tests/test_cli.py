"""Testy CLI pomocníkov."""
from vyuct.cli import lock_path


def test_lock_path_per_instance():
    a = lock_path('https://odoo.example.com', 251)
    b = lock_path('https://odoo.other-example.com', 251)
    c = lock_path('https://odoo.example.com', 269)
    assert a == '/tmp/vyuctovanie-odoo.example.com-251.lock'
    assert len({a, b, c}) == 3


def _settlement_action():
    import datetime as dt
    tz = dt.timezone(dt.timedelta(hours=2))
    od = dt.datetime(2026, 8, 19, 10, 0, tzinfo=tz)
    do = dt.datetime(2026, 9, 1, 18, 0, tzinfo=tz)
    items = [(od, 'Ján Novák', 4.0, 'práca')]
    return ('settlement', 4.0, od, do, items)


def _patch_pipeline(monkeypatch, action):
    from vyuct import cli
    monkeypatch.setattr(cli, 'load_key', lambda: 'k')
    monkeypatch.setattr(cli, 'bot_partner_id', lambda key: 1)
    monkeypatch.setattr(cli, 'fetch_messages', lambda key, ch: [])
    monkeypatch.setattr(cli, 'enrich', lambda raw, pid: [])
    monkeypatch.setattr(cli, 'decide', lambda msgs, now, force_info=False: [action])
    return cli


def test_settlement_attaches_xlsx(monkeypatch):
    action = _settlement_action()
    cli = _patch_pipeline(monkeypatch, action)
    calls = {}

    def fake_build(od, do, items, client):
        calls['build'] = (od, do, items, client)
        return b'XLSXBYTES'

    def fake_create(key, name, data, **kw):
        calls['create'] = (name, data)
        return 4711

    def fake_post(key, ch, body, attachment_ids=None):
        calls['post'] = attachment_ids
        return {'ok': 1}

    monkeypatch.setattr(cli, 'build_xlsx', fake_build)
    monkeypatch.setattr(cli, 'create_attachment', fake_create)
    monkeypatch.setattr(cli, 'post_message', fake_post)
    rc = cli.main(['--channel', '991'])
    assert rc == 0
    assert calls['build'][2] == action[4]          # items odovzdané do build_xlsx
    assert calls['create'][1] == b'XLSXBYTES'       # bytes idú do prílohy
    assert calls['post'] == [4711]                  # message_post dostane attachment_ids


def test_dry_run_generates_file_and_does_not_post(monkeypatch, caplog):
    import os
    action = _settlement_action()
    cli = _patch_pipeline(monkeypatch, action)
    flags = {'posted': False, 'created': False}

    def fake_create(*a, **k):
        flags['created'] = True
        return 1

    def fake_post(*a, **k):
        flags['posted'] = True

    monkeypatch.setattr(cli, 'create_attachment', fake_create)
    monkeypatch.setattr(cli, 'post_message', fake_post)
    caplog.set_level('INFO')
    rc = cli.main(['--dry-run', '--channel', '992'])
    assert rc == 0
    assert flags['posted'] is False                  # nič sa neposlalo
    assert flags['created'] is False                 # ani príloha sa nevytvorila
    # v logu je cesta k vygenerovanému súboru a súbor existuje
    found = None
    for r in caplog.records:
        for tok in r.getMessage().split():
            if tok.endswith('.xlsx') and os.path.exists(tok):
                found = tok
    assert found, 'dry-run mal vygenerovať a zalogovať cestu k .xlsx'
    os.remove(found)


def _info_action():
    import datetime as dt
    tz = dt.timezone(dt.timedelta(hours=2))
    d = dt.datetime(2026, 8, 25, 20, 0, tzinfo=tz)
    return ('info', 4.0, [(d, 'Ján Novák', 4.0, 'práca')])


def test_info_action_posts_without_attachment(monkeypatch):
    action = _info_action()
    cli = _patch_pipeline(monkeypatch, action)
    calls = {'built': False, 'created': False, 'post_att': 'UNSET'}

    def fake_build(*a, **k):
        calls['built'] = True
        return b'X'

    def fake_create(*a, **k):
        calls['created'] = True
        return 1

    def fake_post(key, ch, body, attachment_ids=None):
        calls['post_att'] = attachment_ids
        return {'ok': 1}

    monkeypatch.setattr(cli, 'build_xlsx', fake_build)
    monkeypatch.setattr(cli, 'create_attachment', fake_create)
    monkeypatch.setattr(cli, 'post_message', fake_post)
    rc = cli.main(['--channel', '993'])
    assert rc == 0
    assert calls['built'] is False        # info negeneruje XLSX
    assert calls['created'] is False      # ani prílohu
    assert calls['post_att'] is None      # message_post bez attachment_ids
