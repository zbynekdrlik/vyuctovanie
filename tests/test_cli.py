"""Testy CLI pomocníkov."""
from vyuct.cli import lock_path


def test_lock_path_per_instance():
    a = lock_path('https://odoo.example.com', 251)
    b = lock_path('https://odoo.other-example.com', 251)
    c = lock_path('https://odoo.example.com', 269)
    assert a == '/tmp/vyuctovanie-odoo.example.com-251.lock'
    assert len({a, b, c}) == 3
