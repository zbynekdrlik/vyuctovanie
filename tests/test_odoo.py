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
