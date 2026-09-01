"""Konfigurácia (env-first; zákaznícke hodnoty žijú MIMO repo v ~/.config/vyuct/<meno>.env)."""
import os
from zoneinfo import ZoneInfo


def _parse_rates(raw):
    """'Meno=15;Iné Meno=40' → {meno: sadzba}; prázdny vstup → {}."""
    out = {}
    for part in raw.split(';'):
        part = part.strip()
        if not part:
            continue
        name, sep, val = part.rpartition('=')
        if not sep or not name.strip():
            raise SystemExit(f'VYUCT_RATES: nerozumiem položke „{part}" — formát je Meno=sadzba;…')
        out[name.strip()] = float(val)
    return out


URL = os.environ.get('ODOO_URL', '')
DB = os.environ.get('ODOO_DB', 'odoo')
KEY_FILE = os.path.expanduser(os.environ.get('ODOO_KEY_FILE', ''))
BOT_LOGIN = os.environ.get('ODOO_BOT_LOGIN', '')
CHANNEL_ID = int(os.environ.get('VYUCT_CHANNEL_ID', '0'))
RATE_EUR = float(os.environ.get('VYUCT_RATE_EUR', '0'))
RATES = _parse_rates(os.environ.get('VYUCT_RATES', ''))
CLIENT_NAME = os.environ.get('VYUCT_CLIENT_NAME', '') or None
TZ = ZoneInfo('Europe/Bratislava')
SETTLEMENT_MARK = 'VYÚČTOVANIE'
INFO_MARK = 'Priebežné info'


def rate_for(author):
    """Sadzba pre autora — VYUCT_RATES (per osoba) má prednosť, inak VYUCT_RATE_EUR."""
    if author in RATES:
        return RATES[author]
    if RATE_EUR > 0:
        return RATE_EUR
    raise SystemExit(f'Neznáma sadzba pre autora „{author}" — doplň ho do VYUCT_RATES.')


def validate(channel_id):
    """Zlyhaj nahlas, keď chýba zákaznícky config (env / ~/.config/vyuct/<meno>.env)."""
    missing = [n for n, v in (('ODOO_URL', URL), ('ODOO_KEY_FILE', KEY_FILE),
                              ('ODOO_BOT_LOGIN', BOT_LOGIN)) if not v]
    if channel_id <= 0:
        missing.append('VYUCT_CHANNEL_ID')
    if RATE_EUR <= 0 and not RATES:
        missing.append('VYUCT_RATE_EUR (alebo VYUCT_RATES)')
    if missing:
        raise SystemExit('Chýba konfigurácia: ' + ', '.join(missing)
                         + ' — nastav env / ~/.config/vyuct/<meno>.env')
    if not URL.startswith('https://'):
        raise SystemExit('ODOO_URL musí byť https:// — Bearer kľúč nesmie ísť plaintextom.')
