"""Testy stránkovania fetch_messages (api mockované — externá sieť)."""
import io
import urllib.error
import urllib.request

import pytest

import vyuct.odoo as odoo
from vyuct.odoo import api


def test_fetch_pagination_exact_multiple(monkeypatch):
    pages = {0: [{'id': i} for i in range(200)], 200: []}
    calls = []

    def fake_api(path, payload, key):
        calls.append(payload['offset'])
        return pages[payload['offset']]

    monkeypatch.setattr(odoo, 'api', fake_api)
    out = odoo.fetch_messages('k', 251)
    assert len(out) == 200
    assert calls == [0, 200]


def test_api_401_hints_key_expiry(monkeypatch):
    def fake_urlopen(req, timeout=30):
        raise urllib.error.HTTPError('https://x/json/2/x', 401, 'Unauthorized',
                                     {}, io.BytesIO(b'unauthorized'))
    monkeypatch.setattr(urllib.request, 'urlopen', fake_urlopen)
    with pytest.raises(SystemExit) as ei:
        api('res.users/search_read', {}, 'zly-kluc')
    assert '401' in str(ei.value)
    assert 'expirovať' in str(ei.value)


def test_create_attachment_builds_payload_and_returns_id(monkeypatch):
    seen = {}

    def fake_api(path, payload, key):
        seen['path'] = path
        seen['payload'] = payload
        return [4711]  # JSON-2 create vracia zoznam intov (overené naživo)

    monkeypatch.setattr(odoo, 'api', fake_api)
    att_id = odoo.create_attachment('k', 'Vykaz.xlsx', b'binary-bytes')
    assert att_id == 4711
    assert seen['path'] == 'ir.attachment/create'
    vals = seen['payload']['vals_list'][0]
    assert vals['name'] == 'Vykaz.xlsx'
    assert vals['mimetype'] == \
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    import base64
    assert base64.b64decode(vals['datas']) == b'binary-bytes'


def test_post_message_includes_attachment_ids_when_given(monkeypatch):
    seen = {}
    monkeypatch.setattr(odoo, 'api', lambda p, payload, k: seen.update(payload) or {'ok': 1})
    odoo.post_message('k', 251, '<p>hi</p>', attachment_ids=[4711])
    assert seen['attachment_ids'] == [4711]
    assert seen['body_is_html'] is True


def test_post_message_omits_attachment_ids_by_default(monkeypatch):
    seen = {}
    monkeypatch.setattr(odoo, 'api', lambda p, payload, k: seen.update(payload) or {'ok': 1})
    odoo.post_message('k', 251, '<p>hi</p>')
    assert 'attachment_ids' not in seen
