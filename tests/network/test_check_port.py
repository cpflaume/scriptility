"""Tests für scripts/network/check_port.py"""

from __future__ import annotations

import socket
import threading
from contextlib import contextmanager

import pytest

from scripts.network.check_port import check_port, main


@contextmanager
def listening_socket():
    """Startet einen lokalen TCP-Listener auf einem freien Port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]

    def accept_loop():
        try:
            while True:
                conn, _ = s.accept()
                conn.close()
        except OSError:
            return

    t = threading.Thread(target=accept_loop, daemon=True)
    t.start()
    try:
        yield port
    finally:
        s.close()


def test_check_port_open():
    with listening_socket() as port:
        result = check_port("127.0.0.1", port, timeout=2.0)
    assert result["open"] is True
    assert result["error"] is None


def test_check_port_closed():
    # Port 1 ist mit hoher Wahrscheinlichkeit geschlossen.
    result = check_port("127.0.0.1", 1, timeout=0.5)
    assert result["open"] is False
    assert result["error"] is not None


def test_main_exits_zero_when_open(capsys):
    with listening_socket() as port:
        rc = main(["--host", "127.0.0.1", "--port", str(port), "--timeout", "1", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"open": true' in out


def test_main_exits_one_when_closed():
    rc = main(["--host", "127.0.0.1", "--port", "1", "--timeout", "0.5"])
    assert rc == 1


def test_main_invalid_args_exits_two():
    with pytest.raises(SystemExit) as exc:
        main([])  # missing --host/--port
    assert exc.value.code == 2
