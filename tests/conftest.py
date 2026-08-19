"""Testovací env — čisto syntetické hodnoty, žiadne reálne údaje."""
import os

os.environ.setdefault('ODOO_URL', 'https://odoo.example.com')
os.environ.setdefault('ODOO_DB', 'test')
os.environ.setdefault('ODOO_KEY_FILE', '/tmp/vyuct-test.key')
os.environ.setdefault('ODOO_BOT_LOGIN', 'bot@example.com')
os.environ.setdefault('VYUCT_CHANNEL_ID', '999')
os.environ.setdefault('VYUCT_RATE_EUR', '10')
