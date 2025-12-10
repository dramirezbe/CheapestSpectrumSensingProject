import io
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import demod_consumer
from demod_consumer import (
    float_to_plain,
    Demodulator,
    numeric_type,
    build_parser,
)


# ============================================================================
# float_to_plain
# ============================================================================

def test_float_to_plain_int():
    assert float_to_plain(10.0) == "10"
    assert float_to_plain("20") == "20"


def test_float_to_plain_float():
    assert float_to_plain(10.5) == "10.5"
    assert float_to_plain("123.4500") == "123.45"


def test_float_to_plain_invalid():
    assert float_to_plain("abc") == "abc"


# ============================================================================
# Demodulator: decimation helpers
# ============================================================================

def test_decimation_from_bw():
    d = Demodulator(2_000_000, 200_000, "FM")
    assert d._calc_decimation_from_bw() == 10


def test_decimation_to_target():
    d = Demodulator(2_000_000, 200_000, "AM", decimate_to=500_000)
    assert d._calc_decimation_to_target() == 4


def test_fir_cutoff_for_decimation():
    d = Demodulator(1e6, 1e5, "FM")
    assert d._fir_cutoff_for_decimation(4) == 0.5 / 4


# ============================================================================
# Demodulator: pipelines
# ============================================================================

def test_build_fm_pipeline_basic():
    d = Demodulator(2_000_000, 200_000, "FM")
    pipe = d.build_pipeline()
    assert "fmdemod_quadri_cf" in pipe
    assert "fir_decimate_cc" in pipe
    assert "play" in pipe


def test_build_am_pipeline_basic():
    d = Demodulator(2_000_000, 200_000, "AM")
    pipe = d.build_pipeline()
    assert "amdemod_cf" in pipe
    assert "dcblock_ff" in pipe
    assert "play" in pipe


def test_build_pipeline_invalid():
    d = Demodulator(2_000_000, 200_000, "XYZ")
    with pytest.raises(ValueError):
        d.build_pipeline()


# ============================================================================
# numeric_type
# ============================================================================

def test_numeric_type_valid():
    assert numeric_type("1.23") == 1.23


def test_numeric_type_invalid():
    with pytest.raises(Exception):
        numeric_type("abc")


# ============================================================================
# Parser
# ============================================================================

@patch("sys.argv", ["prog"])
def test_build_parser_no_args():
    with pytest.raises(SystemExit):
        build_parser()


@patch("sys.argv", ["prog", "-f", "100e6", "-t", "FM", "-s", "2e6", "-b", "200k"])
def test_build_parser_valid():
    p = build_parser()
    args = p.parse_args()
    assert args.freq == 100e6
    assert args.type == "FM"
    assert args.rate == 2e6


# ============================================================================
# Demodulator.run
# ============================================================================

@patch("subprocess.Popen")
def test_demod_run_without_metrics(mock_popen):
    """
    Simula datos cortos en stdin, sin métricas.
    """
    fake_proc = MagicMock()
    fake_proc.stdin = MagicMock()
    fake_proc.wait.return_value = 0
    mock_popen.return_value = fake_proc

    # Simula lectura de datos: chunk + EOF
    with patch("demod_consumer.sys.stdin.buffer.read", side_effect=[b"\x01\x02"*1000, b""]):
        d = Demodulator(2_000_000, 200_000, "FM")
        rc = d.run(verbose=False, metrics=False)
        assert rc == 0
        assert fake_proc.stdin.write.call_count == 1


@patch("subprocess.Popen")
def test_demod_run_with_metrics_fm(mock_popen):
    """
    Simula FM con métricas habilitadas.
    """
    fake_proc = MagicMock()
    fake_proc.stdin = MagicMock()
    fake_proc.wait.return_value = 0
    mock_popen.return_value = fake_proc

    # Simula chunk con IQ y luego EOF
    raw = bytes([1, 2, 3, 4, 5, 6, 7, 8])
    with patch("demod_consumer.sys.stdin.buffer.read", side_effect=[raw, b""]):
        d = Demodulator(1_000_000, 100_000, "FM")
        rc = d.run(verbose=False, metrics=True)

    assert rc == 0


@patch("subprocess.Popen")
def test_demod_run_keyboard_interrupt(mock_popen):
    """
    Simula KeyboardInterrupt en lectura.
    """
    fake_proc = MagicMock()
    fake_proc.stdin = MagicMock()
    mock_popen.return_value = fake_proc

    with patch("demod_consumer.sys.stdin.buffer.read", side_effect=KeyboardInterrupt):
        d = Demodulator(1_000_000, 100_000, "FM")
        rc = d.run()
        assert rc == 0


# ============================================================================
# main()
# ============================================================================

@patch("demod_consumer.Demodulator")
@patch("demod_consumer.build_parser")
def test_main_flow(mock_parser, mock_demod):
    parser_mock = MagicMock()
    parser_mock.parse_args.return_value = MagicMock(
        freq=100e6,
        type="FM",
        rate=2e6,
        bw=200e3,
        dec=2e6,
        aud_rate=48000,
        verbose=False,
        metrics=False,
    )
    mock_parser.return_value = parser_mock

    demod_instance = MagicMock()
    demod_instance.run.return_value = 0
    mock_demod.return_value = demod_instance

    assert demod_consumer.main() == 0
    demod_instance.run.assert_called_once()


# ============================================================================
# __main__ entrypoint
# ============================================================================

@patch("demod_consumer.cfg")
@patch("demod_consumer.sys")
def test_entrypoint(mock_sys, mock_cfg):
    mock_cfg.LOG_FILES_NUM = 5
    mock_cfg.run_and_capture.return_value = 123

    with patch("demod_consumer.__name__", "__main__"):
        from importlib import reload
        reload(demod_consumer)

    mock_cfg.run_and_capture.assert_called_once()
    mock_sys.exit.assert_called_once_with(123)
