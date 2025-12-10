import pytest
from fastapi.testclient import TestClient
import numpy as np

from Fast_api_server import (
    app,
    SENSOR_MAC,
    pending_config,
    last_result,
)

client = TestClient(app)


# -----------------------------------------
# FIXTURE: Limpiar estado antes de cada test
# -----------------------------------------
@pytest.fixture(autouse=True)
def clean_state():
    global pending_config, last_result
    pending_config = None
    last_result = None
    yield
    pending_config = None
    last_result = None


# ===============================================================
# 1) TEST: POST /configuration
# ===============================================================

def test_set_configuration_ok():
    payload = {
        "center_frequency": 98_000_000,
        "span": 20_000_000,
        "resolution_hz": 10000
    }

    res = client.post("/configuration", json=payload)
    assert res.status_code == 200

    body = res.json()
    assert body["status"] == "ok"
    assert body["mac"] == SENSOR_MAC

    # pending_config debe haberse guardado
    assert pending_config is not None
    assert pending_config["center_frequency"] == 98_000_000


# ===============================================================
# 2) TEST: GET /{mac}/configuration
# ===============================================================

def test_get_configuration_ok():
    # Primero enviar configuración válida
    client.post("/configuration", json={
        "center_frequency": 98_000_000,
        "span": 20_000_000
    })

    res = client.get(f"/{SENSOR_MAC}/configuration")
    assert res.status_code == 200

    data = res.json()
    assert data["center_frequency"] == 98_000_000
    assert data["span"] == 20_000_000


def test_get_configuration_wrong_mac():
    client.post("/configuration", json={
        "center_frequency": 98_000_000,
        "span": 20_000_000
    })

    res = client.get("/AA:BB:CC:DD:EE:FF/configuration")
    assert res.status_code == 404
    assert res.json()["detail"] == "Unknown MAC"


def test_get_configuration_no_config():
    res = client.get(f"/{SENSOR_MAC}/configuration")
    assert res.status_code == 404
    assert res.json()["detail"] == "No configuration set"


# ===============================================================
# 3) TEST: POST /data  (recibir PSD)
# ===============================================================

def test_post_data_ok():
    meas = {
        "Pxx": [-80, -70, -60],
        "start_freq_hz": 1e6,
        "end_freq_hz": 2e6,
        "timestamp": 123456,
        "mac": SENSOR_MAC
    }

    res = client.post("/data", json=meas)
    assert res.status_code == 200

    body = res.json()
    assert body["status"] == "ok"
    assert last_result is not None
    assert last_result["Pxx"] == [-80, -70, -60]


def test_post_data_invalid_mac():
    meas = {
        "Pxx": [-80, -70],
        "start_freq_hz": 1e6,
        "end_freq_hz": 2e6,
        "timestamp": 111,
        "mac": "11:22:33:44:55"
    }

    res = client.post("/data", json=meas)
    assert res.status_code == 400
    assert res.json()["detail"] == "MAC mismatch"


# ===============================================================
# 4) TEST: GET /last_result
# ===============================================================

def test_last_result_ok():
    # Inyectar manualmente un resultado
    global last_result
    last_result = {
        "Pxx": [-90, -80],
        "start_freq_hz": 1000,
        "end_freq_hz": 2000,
        "timestamp": 999,
        "mac": SENSOR_MAC
    }

    res = client.get("/last_result")
    assert res.status_code == 200
    assert res.json()["timestamp"] == 999


def test_last_result_empty():
    res = client.get("/last_result")
    assert res.status_code == 404
    assert res.json()["detail"] == "No result available"


# ===============================================================
# 5) TEST: GET /psd_plot.png
# ===============================================================

def test_psd_plot_ok():
    global last_result
    last_result = {
        "Pxx": [-80, -70, -75],
        "start_freq_hz": 1e6,
        "end_freq_hz": 2e6,
        "timestamp": 10,
        "mac": SENSOR_MAC
    }

    res = client.get("/psd_plot.png")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_psd_plot_invalid_no_result():
    res = client.get("/psd_plot.png")
    assert res.status_code == 404


def test_psd_plot_invalid_data():
    global last_result
    last_result = {
        "Pxx": [],
        "start_freq_hz": 2e6,
        "end_freq_hz": 1e6,
        "timestamp": 123,
        "mac": SENSOR_MAC
    }

    res = client.get("/psd_plot.png")
    assert res.status_code == 400


# ===============================================================
# 6) TEST: GET /psd_live  (HTML)
# ===============================================================

def test_live_page_renders():
    res = client.get("/psd_live")
    assert res.status_code == 200
    assert "<html" in res.text.lower()
    assert "PSD en vivo" in res.text
