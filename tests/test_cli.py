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
    from vyuct import cli
    calls = {}
    action = _settlement_action()
    cli = _patch_pipeline(monkeypatch, action)
    monkeypatch.setattr(cli, 'build_xlsx',
                        lambda od, do, items, client: calls.setdefault('build', (od, do, items, client)) or b'XLSXBYTES')
    monkeypatch.setattr(cli, 'create_attachment',
                        lambda key, name, data, **kw: calls.setdefault('create', (name, data)) or 4711)
    monkeypatch.setattr(cli, 'post_message',
                        lambda key, ch, body, attachment_ids=None: calls.setdefault('post', attachment_ids))
    rc = cli.main(['--channel', '999'])
    assert rc == 0
    assert calls['build'][2] == action[4]          # items odovzdané do build_xlsx
    assert calls['create'][1] == b'XLSXBYTES'       # bytes idú do prílohy
    assert calls['post'] == [4711]                  # message_post dostane attachment_ids


def test_dry_run_generates_file_and_does_not_post(monkeypatch, caplog):
    import os
    from vyuct import cli
    posted = {'called': False}
    action = _settlement_action()
    cli = _patch_pipeline(monkeypatch, action)
    monkeypatch.setattr(cli, 'create_attachment',
                        lambda *a, **k: posted.update(created=True) or 1)
    monkeypatch.setattr(cli, 'post_message',
                        lambda *a, **k: posted.update(called=True))
    caplog.set_level('INFO')
    rc = cli.main(['--dry-run', '--channel', '999'])
    assert rc == 0
    assert posted['called'] is False                 # nič sa neposlalo
    assert 'created' not in posted                    # ani príloha sa nevytvorila
    # v logu je cesta k vygenerovanému súboru a súbor existuje
    paths = [r.getMessage() for r in caplog.records if '.xlsx' in r.getMessage()]
    assert paths, 'dry-run mal zalogovať cestu k .xlsx'
    found = None
    for msg in paths:
        for tok in msg.split():
            if tok.endswith('.xlsx') and os.path.exists(tok):
                found = tok
    assert found and os.path.exists(found)
    os.remove(found)
