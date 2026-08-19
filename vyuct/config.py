"""Konfigurácia (env-first; zákaznícke hodnoty žijú MIMO repo v ~/.config/vyuct/<meno>.env)."""
import os
from zoneinfo import ZoneInfo

URL = os.environ.get('ODOO_URL', '')
DB = os.environ.get('ODOO_DB', 'odoo')
KEY_FILE = os.path.expanduser(os.environ.get('ODOO_KEY_FILE', ''))
BOT_LOGIN = os.environ.get('ODOO_BOT_LOGIN', '')
CHANNEL_ID = int(os.environ.get('VYUCT_CHANNEL_ID', '0'))
RATE_EUR = float(os.environ.get('VYUCT_RATE_EUR', '0'))
TZ = ZoneInfo('Europe/Bratislava')
SETTLEMENT_MARK = 'VYÚČTOVANIE'
INFO_MARK = 'Priebežné info'


def validate(channel_id):
    """Zlyhaj nahlas, keď chýba zákaznícky config (env / ~/.config/vyuct/<meno>.env)."""
    missing = [n for n, v in (('ODOO_URL', URL), ('ODOO_KEY_FILE', KEY_FILE),
                              ('ODOO_BOT_LOGIN', BOT_LOGIN)) if not v]
    if channel_id <= 0:
        missing.append('VYUCT_CHANNEL_ID')
    if RATE_EUR <= 0:
        missing.append('VYUCT_RATE_EUR')
    if missing:
        raise SystemExit('Chýba konfigurácia: ' + ', '.join(missing)
                         + ' — nastav env / ~/.config/vyuct/<meno>.env')
    if not URL.startswith('https://'):
        raise SystemExit('ODOO_URL musí byť https:// — Bearer kľúč nesmie ísť plaintextom.')
