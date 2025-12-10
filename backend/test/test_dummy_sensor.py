import pytest
import numpy as np
import json
from dummy_sensor import (
    generate_dummy_spectrum,
    print_verbose_json,
    SENSOR_MAC
)

# ---------------------------
# Test: generate_dummy_spectrum
# ---------------------------

def test_generate_dummy_spectrum_basic():
    config = {
        "center_freq_hz": 10_000_000,
        "span": 20_000_000,
        "resolution_hz": 10_000
    }

    result = generate_dummy_spectrum(config)

    # Validate structure
    assert "mac" in result
    assert "Pxx" in result
    assert "start_freq_hz" in result
    assert "end_freq_hz" in result
    assert "timestamp" in result

    # mac is correct
    assert result["mac"] == SENSOR_MAC

    # Pxx array has correct size
    expected_bins = int(config["span"] / config["resolution_hz"])
    assert len(result["Pxx"]) == expected_bins

    # Frequency calculations
    assert result["start_freq_hz"] == config["center_freq_hz"] - config["span"] / 2
    assert result["end_freq_hz"] == config["center_freq_hz"] + config["span"] / 2

    # Pxx contains floats
    assert all(isinstance(v, float) for v in result["Pxx"])

def test_generate_dummy_spectrum_rbw_zero():
    """Si resolution_hz es 0, debe usarse el fallback 10000."""
    config = {
        "center_freq_hz": 10_000_000,
        "span": 20_000_000,
        "resolution_hz": 0
    }

    result = generate_dummy_spectrum(config)
    expected_bins = int(config["span"] / 10000)  # fallback RBW
    assert len(result["Pxx"]) == expected_bins


# ---------------------------
# Test: print_verbose_json
# ---------------------------

def test_print_verbose_json_does_not_crash(capsys):
    """Solo verificar que imprime algo y no lanza errores."""
    data = {"Pxx": list(np.random.randn(20))}
    print_verbose_json("TEST LABEL", data)

    captured = capsys.readouterr()
    assert "TEST LABEL" in captured.out
