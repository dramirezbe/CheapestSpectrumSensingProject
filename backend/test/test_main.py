import pytest
from fastapi.testclient import TestClient
import numpy as np

from main import (
    app,
    device_state,
    VALID_MACS,
    load_valid_macs,
    get_device_store,
    calculate_rf_metrics,
)

client = TestClient(app)

# ---------------------------
#  FIXTURES
# ---------------------------

@pytest.fixture
def any_mac():
    """Devuelve un MAC válido para las pruebas."""
    return next(iter(VALID_MACS))


@pytest.fixture(autouse=True)
def clear_state():
    """Resetea device_state entre tests."""
    device_state.clear()
    yield
    device_state.clear()


# ---------------------------
#  TEST: Helper Functions
# ---------------------------

def test_load_valid_macs_returns_set():
    macs = load_valid_macs()
    assert isinstance(macs, set)
    assert len(macs) > 0


def test_get_device_store_initializes(any_mac):
    store = get_device_store(any_mac)
    assert "config" in store
    assert "metrics" in store
    assert "data" in store
    assert any_mac in device_state


def test_get_device_store_invalid_mac():
    with pytest.raises(Exception):
        get_device_store("11:22:33:44:55:66")


def test_calculate_rf_metrics_empty():
    result = calculate_rf_metrics([])
    assert result["noise_floor_dbm"] == 0
    assert result["peak_power_dbm"] == 0
    assert result["snr_db"] == 0


def test_calculate_rf_metrics_normal():
    pxx = [-90, -80, -85, -70]
    result = calculate_rf_metrics(pxx)
    assert result["peak_power_dbm"] == -70
    assert result["noise_floor_dbm"] == pytest.approx(np.median(pxx), 0.1)
    assert "snr_db" in result


# ---------------------------
#  TEST: FRONTEND ENDPOINTS
# ---------------------------

def test_frontend_metrics_default(any_mac):
    res = client.get("/api/v1/front/metrics", params={"mac": any_mac})
    assert res.status_code == 200
    assert res.json() == {}  # metrics vacío al inicio


def test_frontend_data_empty(any_mac):
    res = client.get("/api/v1/front/data", params={"mac": any_mac})
    assert res.status_code == 200
    body = res.json()
    assert body["Pxx"] == []
    assert body["metrics"] == {}


def test_frontend_data_with_pxx(any_mac):
    # Insertar datos simulados
    device_state[any_mac] = {
        "config": {},
        "metrics": {},
        "data": {
            "start_freq_hz": 1,
            "end_freq_hz": 2,
            "center_freq_hz": 1,
            "timestamp": 123,
            "Pxx": [-80, -70, -60]
        },
    }

    res = client.get("/api/v1/front/data", params={"mac": any_mac})
    assert res.status_code == 200
    data = res.json()
    assert data["metrics"]["peak_power_dbm"] == -60


def test_frontend_update_params(any_mac):
    payload = {"mac": any_mac, "params": {"center_freq_hz": 999}}
    res = client.post("/api/v1/front/params", json=payload)
    assert res.status_code == 200
    assert device_state[any_mac]["config"] == {"center_freq_hz": 999}


# ---------------------------
#  TEST: SENSOR ENDPOINTS
# ---------------------------

def test_sensor_realtime(any_mac):
    res = client.get(f"/api/v1/{any_mac}/realtime")
    assert res.status_code == 200
    assert "center_freq_hz" in res.json()


def test_sensor_post_metrics(any_mac):
    payload = {"temp": 45, "cpu": 12}
    res = client.post(f"/api/v1/{any_mac}/metrics", json=payload)

    assert res.status_code == 200
    assert device_state[any_mac]["metrics"] == payload


def test_sensor_post_data(any_mac):
    payload = {"Pxx": [-90, -85, -80]}
    res = client.post(f"/api/v1/{any_mac}/data", json=payload)

    assert res.status_code == 200
    assert device_state[any_mac]["data"]["Pxx"] == [-90, -85, -80]


def test_sensor_post_data_invalid_mac():
    res = client.post("/api/v1/11:22:33:44:55:66/data", json={"Pxx": [1, 2]})
    assert res.status_code == 403
