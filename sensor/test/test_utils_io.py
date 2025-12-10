import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from utils.io_util import (
    atomic_write_bytes,
    get_persist_var,
    modify_persist,
    CronHandler,
    ElapsedTimer,
)


# ---------------------------------------------------------
# atomic_write_bytes
# ---------------------------------------------------------

def test_atomic_write_bytes_writes_data(tmp_path):
    target = tmp_path / "data.bin"
    data = b"hello world"

    atomic_write_bytes(target, data)

    assert target.exists()
    assert target.read_bytes() == data


def test_atomic_write_bytes_overwrites(tmp_path):
    target = tmp_path / "data.bin"
    target.write_bytes(b"old data")

    new_data = b"new data"
    atomic_write_bytes(target, new_data)

    assert target.read_bytes() == new_data


# ---------------------------------------------------------
# get_persist_var
# ---------------------------------------------------------

def test_get_persist_var_returns_value(tmp_path):
    path = tmp_path / "vars.json"
    path.write_text(json.dumps({"x": 123}))

    assert get_persist_var("x", path) == 123


def test_get_persist_var_nonexistent_file(tmp_path):
    path = tmp_path / "missing.json"
    assert get_persist_var("x", path) is None


def test_get_persist_var_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not-json")

    assert get_persist_var("x", path) is None


def test_get_persist_var_not_dict(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps([1, 2, 3]))  # JSON válido pero no dict

    assert get_persist_var("x", path) is None


# ---------------------------------------------------------
# modify_persist
# ---------------------------------------------------------

def test_modify_persist_creates_file(tmp_path):
    path = tmp_path / "vars.json"
    
    rc = modify_persist("a", 99, path)
    assert rc == 0

    data = json.loads(path.read_text())
    assert data["a"] == 99


def test_modify_persist_updates_existing(tmp_path):
    path = tmp_path / "vars.json"
    path.write_text(json.dumps({"a": 1}))

    modify_persist("a", 999, path)

    data = json.loads(path.read_text())
    assert data["a"] == 999


def test_modify_persist_overwrites_invalid_json(tmp_path, caplog):
    path = tmp_path / "vars.json"
    path.write_text("INVALID JSON")

    modify_persist("x", 42, path)

    data = json.loads(path.read_text())
    assert data["x"] == 42


# ---------------------------------------------------------
# CronHandler
# ---------------------------------------------------------

@pytest.fixture
def mock_crontab():
    """Mock CronTab to avoid modifying real system crontab."""
    with patch("utils.io_util.CronTab") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


def test_cronhandler_init(mock_crontab):
    handler = CronHandler(get_time_ms=lambda: 1000)
    assert handler.cron is mock_crontab


def test_cronhandler_is_in_activate_time():
    handler = CronHandler(get_time_ms=lambda: 2000)

    # guard window = ±10,000 ms → always true here
    assert handler.is_in_activate_time(0, 1000)


def test_cronhandler_add_creates_job(mock_crontab):
    handler = CronHandler(get_time_ms=lambda: 0)
    rc = handler.add("echo test", "myjob", 5)

    assert rc == 0
    assert handler.crontab_changed is True
    mock_crontab.new.assert_called_once()


def test_cronhandler_add_invalid_minutes(mock_crontab):
    handler = CronHandler(get_time_ms=lambda: 0)
    rc = handler.add("echo test", "myjob", 0)  # inválido
    assert rc == 1


def test_cronhandler_erase(mock_crontab):
    fake_job = MagicMock()
    mock_crontab.find_comment.return_value = [fake_job]

    handler = CronHandler(get_time_ms=lambda: 0)
    handler.erase("myjob")

    mock_crontab.remove.assert_called_once_with(fake_job)


def test_cronhandler_save(mock_crontab):
    handler = CronHandler(get_time_ms=lambda: 0)
    handler.crontab_changed = True

    rc = handler.save()

    assert rc == 0
    mock_crontab.write.assert_called_once()


# ---------------------------------------------------------
# ElapsedTimer
# ---------------------------------------------------------

def test_elapsed_timer():
    timer = ElapsedTimer()
    timer.init_count(0.1)

    assert not timer.time_elapsed()
    time.sleep(0.15)
    assert timer.time_elapsed()
