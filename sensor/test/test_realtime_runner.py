import os
import io
import pytest
import time
import signal
import subprocess
from unittest.mock import MagicMock, patch, mock_open

from realtime_runner import (
    float_to_plain,
    build_cmds,
    FifoManager,
    start_consumer_with_fifo,
    start_hackrf,
    tee_stream,
    terminate_process,
    run_pipeline,
)


# =============================================================================
# float_to_plain
# =============================================================================

def test_float_to_plain_int():
    assert float_to_plain(10.0) == "10"
    assert float_to_plain("10") == "10"


def test_float_to_plain_float():
    assert float_to_plain(10.5) == "10.5"
    assert float_to_plain("123.4500") == "123.45"


def test_float_to_plain_invalid():
    assert float_to_plain("abc") == "abc"


# =============================================================================
# build_cmds
# =============================================================================

def test_build_cmds_basic():
    hackrf_cmd, demod_cmd, psd_cmd = build_cmds(
        freq_hz=100_000_000,
        sample_rate_hz=2_000_000,
        freq_plain="100000000",
        sample_rate_plain="2000000",
        rbw=1000,
        demod=None,
        bw=None,
        metrics=False
    )
    assert "hackrf_transfer" in hackrf_cmd
    assert demod_cmd is None
    assert "psd_consumer.py" in psd_cmd


def test_build_cmds_with_demod():
    hackrf_cmd, demod_cmd, psd_cmd = build_cmds(
        100_000_000, 2_000_000,
        "100000000", "2000000",
        1000, demod="FM", bw=200000, metrics=True
    )
    assert "demod_consumer.py" in demod_cmd
    assert "-t FM" in demod_cmd
    assert "-m" in demod_cmd  # metrics flag


# =============================================================================
# FifoManager
# =============================================================================

@patch("os.mkfifo")
def test_fifomanager_create(mock_mkfifo, tmp_path):
    p1 = tmp_path / "fifo1"
    p2 = tmp_path / "fifo2"
    fm = FifoManager([str(p1), str(p2)])
    fm.create()
    assert mock_mkfifo.call_count == 2


@patch("os.unlink")
def test_fifomanager_unlink(mock_unlink, tmp_path):
    p1 = tmp_path / "fifo1"
    p2 = tmp_path / "fifo2"
    fm = FifoManager([str(p1), str(p2)])
    fm.unlink()
    assert mock_unlink.call_count == 2


# =============================================================================
# start_consumer_with_fifo / start_hackrf
# =============================================================================

@patch("subprocess.Popen")
def test_start_consumer_with_fifo(mock_popen):
    cmd = "python3 test.py"
    fifo = "/tmp/fifo_test"
    p = start_consumer_with_fifo(cmd, fifo)
    mock_popen.assert_called_once()
    assert isinstance(p, MagicMock)


@patch("subprocess.Popen")
def test_start_hackrf(mock_popen):
    cmd = "hackrf_transfer -f 100"
    p = start_hackrf(cmd)
    mock_popen.assert_called_once()
    assert isinstance(p, MagicMock)


# =============================================================================
# tee_stream
# =============================================================================

@patch("realtime_runner.get_persist_var")
def test_tee_stream_basic(mock_persist, tmp_path):
    """
    Test tee_stream without real FIFOs.
    Instead: provide BytesIO as `src`.
    Mock open() to return BytesIO for FIFOs.
    """
    mock_persist.return_value = "realtime"

    # Make fake fifo files
    f1 = tmp_path / "fifo1"
    f2 = tmp_path / "fifo2"
    f1.write_text("")  # create file paths
    f2.write_text("")

    fifo_paths = [str(f1), str(f2)]

    # Fake source stream
    src = io.BytesIO(b"A" * 1024 + b"")

    # Fake write-ends for FIFOs
    fake_fd = io.BytesIO()

    def fake_open(path, mode="wb", buffering=0):
        return fake_fd

    with patch("builtins.open", side_effect=fake_open):
        tee_stream(src, fifo_paths, chunk_size=256)

    # Verify some data was written to fake_fd
    assert fake_fd.getvalue().startswith(b"A")


@patch("realtime_runner.get_persist_var", return_value="stop")  # immediately stop
def test_tee_stream_early_exit(mock_persist, tmp_path):
    src = io.BytesIO(b"data")

    f = tmp_path / "fifo"
    f.write_text("")

    # Should exit immediately because current_mode != 'realtime'
    tee_stream(src, [str(f)], chunk_size=128)


# =============================================================================
# terminate_process
# =============================================================================

def test_terminate_process_none():
    # Should simply return and not crash
    terminate_process(None, "testproc")


def test_terminate_process_active():
    proc = MagicMock()
    proc.poll.return_value = None  # pretend still running
    terminate_process(proc, "x")
    proc.terminate.assert_called_once()


# =============================================================================
# run_pipeline
# =============================================================================

@patch("realtime_runner.start_hackrf")
@patch("realtime_runner.start_consumer_with_fifo")
@patch("realtime_runner.FifoManager")
@patch("realtime_runner.build_cmds", return_value=("hack", None, "psd"))
@patch("realtime_runner.tee_stream")
def test_run_pipeline(
    mock_tee,
    mock_build,
    mock_fm,
    mock_consumer,
    mock_hackrf
):
    # Fake processes
    mock_consumer.return_value = MagicMock(stdout=None)
    mock_hackrf.return_value = MagicMock(stdout=io.BytesIO(b"data"))

    rc = run_pipeline(
        freq=100e6,
        rate=2e6,
        rbw=1e3,
        demod=None,
        bw=None,
        metrics=False,
        verbose=False
    )

    assert rc == 0
    mock_fm.return_value.create.assert_called_once()
    mock_consumer.assert_called_once()
    mock_hackrf.assert_called_once()


# =============================================================================
# parse_args
# =============================================================================

@patch("sys.argv", ["prog", "-f", "1000000", "-s", "2000000", "-w", "1000"])
def test_parse_args_valid():
    from realtime_runner import parse_args
    args = parse_args()
    assert args.freq == 1_000_000
    assert args.rate == 2_000_000
    assert args.rbw == 1000


@patch("sys.argv", ["prog"])  # no args → prints help + sys.exit()
def test_parse_args_no_args():
    from realtime_runner import parse_args
    with pytest.raises(SystemExit):
        parse_args()
