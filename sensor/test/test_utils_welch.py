import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from utils.welch_util import WelchEstimator, CampaignHackRF


# =============================================================================
# WelchEstimator
# =============================================================================

def test_next_power_of_2():
    est = WelchEstimator(freq=100e6, fs=1e6, desired_rbw=1e3)
    assert est._next_power_of_2(1) == 1
    assert est._next_power_of_2(2) == 2
    assert est._next_power_of_2(3) == 4
    assert est._next_power_of_2(15) == 16


def test_calculate_desired_nperseg():
    fs = 1_000_000   # 1 MHz
    rbw = 1_000      # 1 kHz → expect nperseg ≈ 1000 → next power of 2 → 1024
    est = WelchEstimator(freq=0, fs=fs, desired_rbw=rbw)
    assert est.desired_nperseg == 1024


def test_execute_welch_returns_shifted_freq_and_psd():
    fs = 1000
    est = WelchEstimator(freq=10_000, fs=fs, desired_rbw=10, with_shift=True)

    iq = np.random.randn(2048) + 1j*np.random.randn(2048)

    f, Pxx = est.execute_welch(iq, scale="dB")

    assert isinstance(f, np.ndarray)
    assert isinstance(Pxx, np.ndarray)
    assert len(f) == len(Pxx)
    assert np.allclose(f.mean(), 10_000, atol=fs/2)  # centered around freq


def test_execute_welch_no_shift():
    fs = 2000
    est = WelchEstimator(freq=10_000, fs=fs, desired_rbw=10, with_shift=False)

    iq = np.random.randn(4096)

    Pxx = est.execute_welch(iq, scale="dBm")

    assert isinstance(Pxx, np.ndarray)


def test_scale_db():
    est = WelchEstimator(freq=0, fs=1000, desired_rbw=10)
    iq = np.ones(1024) * (1 + 1j)

    f, Pxx = est.execute_welch(iq, scale="dB")
    assert np.isfinite(Pxx).all()


def test_scale_dbm():
    est = WelchEstimator(freq=0, fs=1000, desired_rbw=10, r_ant=50.0)
    iq = np.ones(1024) * (1 + 1j)

    f, Pxx = est.execute_welch(iq, scale="dBm")
    assert np.isfinite(Pxx).all()


def test_scale_dbfs():
    """Check that normalization works and dBFS returns finite values."""
    est = WelchEstimator(freq=0, fs=1000, desired_rbw=10)
    iq = np.random.randn(4096)

    f, Pxx = est.execute_welch(iq, scale="dBFS")
    assert np.isfinite(Pxx).all()


def test_scale_v2_hz_with_impedance():
    est = WelchEstimator(freq=0, fs=1000, desired_rbw=10, r_ant=100.0)
    iq = np.random.randn(2048)

    f, Pxx = est.execute_welch(iq, scale="V2/Hz")
    assert np.isfinite(Pxx).all()


def test_scale_invalid():
    est = WelchEstimator(freq=0, fs=1000, desired_rbw=10)
    iq = np.random.randn(1024)

    with pytest.raises(ValueError):
        est.execute_welch(iq, scale="INVALID")


# =============================================================================
# CampaignHackRF
# =============================================================================

@pytest.fixture
def mock_hackrf():
    """Mock HackRF object returned by HackRF()."""
    m = MagicMock()
    m.read_samples.return_value = np.random.randn(4096) + 1j*np.random.randn(4096)
    return m


@patch("utils.welch_util.HackRF")
def test_acquire_hackrf_success(mock_cls, mock_hackrf):
    mock_cls.return_value = mock_hackrf

    camp = CampaignHackRF(
        start_freq_hz=90e6,
        end_freq_hz=110e6,
        sample_rate_hz=1e6,
        resolution_hz=1e3
    )

    rc = camp.acquire_hackrf()
    assert rc == 0
    assert camp.iq is not None
    mock_hackrf.read_samples.assert_called_once()


@patch("utils.welch_util.HackRF")
def test_acquire_hackrf_failure(mock_cls):
    """Simulate HackRF raising an exception on open."""
    mock_cls.side_effect = Exception("device error")

    camp = CampaignHackRF(90e6, 110e6, 1e6, 1e3)
    rc = camp.acquire_hackrf()
    assert rc == 1
    assert camp.iq is None


@patch("utils.welch_util.HackRF")
def test_get_psd_success_with_shift(mock_cls, mock_hackrf):
    mock_cls.return_value = mock_hackrf

    camp = CampaignHackRF(90e6, 110e6, 1e6, 1e3, scale="dB")
    f, Pxx = camp.get_psd()

    assert isinstance(f, np.ndarray)
    assert isinstance(Pxx, np.ndarray)
    assert len(f) == len(Pxx)


@patch("utils.welch_util.HackRF")
def test_get_psd_success_no_shift(mock_cls, mock_hackrf):
    mock_cls.return_value = mock_hackrf

    camp = CampaignHackRF(90e6, 110e6, 1e6, 1e3, scale="dB", with_shift=False)
    Pxx = camp.get_psd()

    assert isinstance(Pxx, np.ndarray)


@patch("utils.welch_util.HackRF")
def test_get_psd_failure(mock_cls):
    """If acquisition fails → return (None, None) for with_shift."""
    mock_cls.side_effect = Exception("open fail")

    camp = CampaignHackRF(90e6, 110e6, 1e6, 1e3)
    f, Pxx = camp.get_psd()

    assert f is None
    assert Pxx is None
