import os
import json
import shutil
import pytest
from unittest.mock import Mock

from metrics_server import (
    MetricsManager,
    fetch_job,
    fetch_data
)


# =========================================================
#  FIXTURE: carpeta temporal para pruebas
# =========================================================
@pytest.fixture
def temp_folder(tmp_path):
    """
    Redirige MetricsManager.folder hacia una carpeta temporal.
    """
    folder = tmp_path / "csv_test"
    folder.mkdir()
    yield str(folder)



# =========================================================
#  TESTS: MetricsManager
# =========================================================

def test_metrics_manager_creation(temp_folder, monkeypatch):
    """
    Verifica que MetricsManager cree la carpeta si no existe.
    """
    # Forzar el folder a nuestro temp_folder
    monkeypatch.setattr(MetricsManager, "folder", temp_folder)

    mgr = MetricsManager("AA:BB:CC")

    assert os.path.exists(mgr.folder)


def test_get_size_metrics_basic():
    mgr = MetricsManager("XX")
    data = {"a": 1, "b": "hola"}

    metrics = mgr.get_size_metrics(data, prefix="test")

    assert "test_bytes" in metrics
    assert metrics["test_bytes"] > 0
    assert metrics["test_KB"] > 0


def test_rotate_files(temp_folder, monkeypatch):
    monkeypatch.setattr(MetricsManager, "folder", temp_folder)

    mgr = MetricsManager("MAC")

    # Crear 105 archivos CSV
    for i in range(105):
        open(os.path.join(temp_folder, f"f{i}.csv"), "w").close()

    mgr.max_files = 100
    mgr.rotate_files()

    remaining = [f for f in os.listdir(temp_folder) if f.endswith(".csv")]
    assert len(remaining) == 100  # debe borrar hasta quedar exactamente 100


def test_save_metrics_creates_file(temp_folder, monkeypatch):
    """
    Verifica que save_metrics crea un archivo CSV correcto.
    """
    monkeypatch.setattr(MetricsManager, "folder", temp_folder)

    mgr = MetricsManager("TESTMAC")

    server_cfg = {"span": 20_000_000, "center_freq_hz": 98e6}
    sent_params = {"start_freq_hz": 1e6, "end_freq_hz": 2e6, "timestamp": 12345}
    metrics = {"fetch_duration_ms": 10.5}

    mgr.save_metrics(server_cfg, sent_params, metrics)

    # Debe existir un archivo CSV
    files = os.listdir(temp_folder)
    assert len(files) == 1
    assert files[0].endswith(".csv")

    # CSV debe tener contenido
    content = open(os.path.join(temp_folder, files[0])).read()
    assert "TESTMAC" in content
    assert "cfg_span" in content
    assert "sent_end_freq_hz" in content



# =========================================================
#  TESTS: fetch_data()
# =========================================================

def test_fetch_data_basic(monkeypatch):
    monkeypatch.setattr("metrics_server.cfg.get_mac", lambda: "MAC123")
    monkeypatch.setattr("metrics_server.cfg.get_time_ms", lambda: 999)

    payload = {
        "Pxx": [1, 2, 3],
        "start_freq_hz": 100,
        "end_freq_hz": 200,
    }

    result = fetch_data(payload)

    assert result["Pxx"] == [1, 2, 3]
    assert result["start_freq_hz"] == 100
    assert result["end_freq_hz"] == 200
    assert result["timestamp"] == 999
    assert result["mac"] == "MAC123"



# =========================================================
#  TESTS: fetch_job()
# =========================================================

def test_fetch_job_success(monkeypatch):
    """
    Mockeamos RequestClient.get() para devolver status 200.
    """
    class MockResp:
        status_code = 200
        def json(self):
            return {
                "center_frequency": 1000,
                "span": 2000,
                "resolution_hz": 100,
            }

    mock_client = Mock()
    mock_client.get.return_value = (0, MockResp())

    monkeypatch.setattr("metrics_server.cfg.get_mac", lambda: "AB:CD")
    job, resp, duration = fetch_job(mock_client)

    assert resp.status_code == 200
    assert job["center_freq_hz"] == 1000
    assert job["span"] == 2000


def test_fetch_job_empty(monkeypatch):
    """
    Caso: resp.json() vacío => fetch_job debe retornar {}.
    """
    class MockResp:
        status_code = 200
        def json(self):
            return {}

    mock_client = Mock()
    mock_client.get.return_value = (0, MockResp())

    monkeypatch.setattr("metrics_server.cfg.get_mac", lambda: "AB:CD")
    job, resp, duration = fetch_job(mock_client)

    assert job == {}
    assert resp.status_code == 200
