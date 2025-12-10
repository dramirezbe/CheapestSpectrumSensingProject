import pytest
import logging
from unittest.mock import mock_open, patch

import cfg


# ======================================================
# 1) get_time_ms
# ======================================================

def test_get_time_ms():
    t1 = cfg.get_time_ms()
    t2 = cfg.get_time_ms()
    assert isinstance(t1, int)
    assert t2 >= t1  # debería aumentar


# ======================================================
# 2) get_mac()  (mock sistema de archivos)
# ======================================================

def test_get_mac_success(monkeypatch):
    """
    Simula /sys/class/net con una interfaz wlan0 y un archivo de MAC válido.
    """

    monkeypatch.setattr("os.listdir", lambda p: ["wlan0", "eth0"])

    fake_mac = "AA:BB:CC:DD:EE:FF"

    # mock de open() para devolver esa MAC
    mock_file = mock_open(read_data=fake_mac)

    with patch("builtins.open", mock_file):
        mac = cfg.get_mac()

    assert mac == fake_mac


def test_get_mac_no_wifi(monkeypatch):
    """
    Si no hay interfaces que empiecen con wlan/wlp => retorna string vacío.
    """
    monkeypatch.setattr("os.listdir", lambda p: ["eth0", "lo"])

    mac = cfg.get_mac()
    assert mac == ""


def test_get_mac_invalid_file(monkeypatch):
    """
    Si open falla, debe continuar silenciosamente => retorna "".
    """
    monkeypatch.setattr("os.listdir", lambda p: ["wlan0"])

    with patch("builtins.open", side_effect=Exception("err")):
        mac = cfg.get_mac()

    assert mac == ""


# ======================================================
# 3) set_logger()
# ======================================================

def test_set_logger_returns_logger():
    logger = cfg.set_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.hasHandlers()


def test_set_logger_idempotent():
    """
    set_logger() debe devolver el mismo logger sin duplicar handlers.
    """
    logger1 = cfg.set_logger()
    handlers_before = len(logger1.handlers)

    logger2 = cfg.set_logger()
    handlers_after = len(logger2.handlers)

    assert logger1 is logger2
    assert handlers_before == handlers_after


# ======================================================
# 4) _CurrentStreamProxy
# ======================================================

def test_current_stream_proxy(monkeypatch):
    proxy = cfg._CurrentStreamProxy("stdout")

    fake_stream = []
    def fake_write(s): fake_stream.append(s)

    class Dummy:
        def write(self, s): fake_write(s)
        def flush(self): pass

    monkeypatch.setattr("sys.stdout", Dummy())

    proxy.write("hola")
    assert fake_stream == ["hola"]


# ======================================================
# 5) Tee class
# ======================================================

def test_tee_writes_to_both():
    buf1 = []
    buf2 = []

    class S1:
        def write(self, s): buf1.append(s)
        def flush(self): pass

    class S2:
        def write(self, s): buf2.append(s)
        def flush(self): pass

    tee = cfg.Tee(S1(), S2())

    tee.write("hello")
    assert buf1 == ["hello"]
    assert buf2 == ["hello"]


# ======================================================
# 6) SimpleFormatter
# ======================================================

def test_simple_formatter_basic():
    fmt = cfg.SimpleFormatter("%(levelname)s:%(message)s", "%H:%M:%S")
    record = logging.LogRecord("x", logging.INFO, "", 0, "hello", None, None)
    text = fmt.format(record)
    assert "INFO" in text
    assert "hello" in text


# ======================================================
# 7) Rutas creadas
# ======================================================

def test_dirs_exist():
    assert cfg.SAMPLES_DIR.exists()
    assert cfg.QUEUE_DIR.exists()
    assert cfg.LOGS_DIR.exists()
    assert cfg.HISTORIC_DIR.exists()
