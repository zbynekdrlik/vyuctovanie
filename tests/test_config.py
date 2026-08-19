"""Testy konfigurácie."""
import pytest

from vyuct import config


def test_validate_fails_loudly_on_missing_config(monkeypatch):
    monkeypatch.setattr(config, 'URL', '')
    with pytest.raises(SystemExit) as ei:
        config.validate(999)
    assert 'ODOO_URL' in str(ei.value)


def test_validate_rejects_zero_rate(monkeypatch):
    monkeypatch.setattr(config, 'RATE_EUR', 0.0)
    with pytest.raises(SystemExit) as ei:
        config.validate(999)
    assert 'VYUCT_RATE_EUR' in str(ei.value)
