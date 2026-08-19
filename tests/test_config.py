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


def test_parse_rates():
    assert config._parse_rates('Ján Novák=15; Peter Kováč=40') == {'Ján Novák': 15.0, 'Peter Kováč': 40.0}
    assert config._parse_rates('') == {}


def test_rate_for_unknown_author_fails_loudly(monkeypatch):
    monkeypatch.setattr(config, 'RATES', {'X': 1.0})
    monkeypatch.setattr(config, 'RATE_EUR', 0.0)
    with pytest.raises(SystemExit):
        config.rate_for('Neznámy')
