import io
import numpy as np
import pytest
from unittest.mock import patch, MagicMock, mock_open

from psd_consumer import (
    plot_psd_png,
    RingBuffer,
    PSDWorker,
    build_arg_parser,
    OUTPUT_FILE,
)


# =============================================================================
# plot_psd_png
# =============================================================================

@patch("matplotlib.pyplot.savefig")
@patch("matplotlib.pyplot.close")
def test_plot_psd_png(mock_close, mock_savefig, tmp_path):
    f = np.linspace(-1e6, 1e6, 1024)
    pxx = np.random.randn(1024)

    # Patch OUTPUT_FILE so the test does not write into project root
    with patch("psd_consumer.OUTPUT_FILE", str(tmp_path / "out.png")):
        plot_psd_png(f, pxx, "dB", fs=1e6, nperseg=512, center_freq=100e6)

    mock_savefig.assert_called_once()


# =============================================================================
# RingBuffer
# =============================================================================

def test_ringbuffer_write_and_read():
    rb = RingBuffer(capacity=10)

    # Write 4 samples
    rb.write(np.array([1+1j, 2+2j, 3+3j, 4+4j]))

    assert rb.count == 4

    latest = rb.read_latest(4)
    assert latest is not None
    assert len(latest) == 4
    assert latest[0] == 1+1j

    # Write more to force wrap-around
    rb.write(np.array([5+5j] * 10))
    assert rb.count == 10  # capacity

    latest = rb.read_latest(10)
    assert len(latest) == 10


def test_ringbuffer_not_enough_data():
    rb = RingBuffer(capacity=10)
    rb.write(np.array([1+1j, 2+2j]))

    assert rb.read_latest(5) is None


# =============================================================================
# PSDWorker – without running infinite loop
# =============================================================================

@patch("psd_consumer.plot_psd_png")
def test_psdworker_basic(mock_plot):
    # Fake ring buffer that always returns enough samples
    rb = MagicMock()
    rb.read_latest.return_value = np.ones(1024, dtype=np.complex128)
    rb.count = 1024
    rb.lock = MagicMock()
    rb.cv = MagicMock()

    # Fake estimator
    est = MagicMock()
    est.execute_welch.return_value = (np.arange(10), np.arange(10))

    logger = MagicMock()

    worker = PSDWorker(rb, est, "dB", samples=1024, logger=logger)

    # Run a single iteration of the loop by patching sleep to throw exception
    with patch("time.sleep", side_effect=Exception("stop")):
        with pytest.raises(Exception):
            worker.run()

    mock_plot.assert_called_once()
    est.execute_welch.assert_called_once()


# =============================================================================
# build_arg_parser
# =============================================================================

@patch("os.sys.argv", ["prog"])
def test_build_arg_parser_no_args():
    """Should print help and exit."""
    from psd_consumer import build_arg_parser
    with pytest.raises(SystemExit):
        build_arg_parser()


@patch("os.sys.argv", ["prog", "-f", "100e6", "-s", "2e6", "-w", "1e3"])
def test_build_arg_parser_valid():
    parser = build_arg_parser()
    args = parser.parse_args()
    assert args.freq == 100e6
    assert args.rate == 2e6
    assert args.rbw == 1e3


# =============================================================================
# main()
# =============================================================================

@patch("psd_consumer.WelchEstimator")
@patch("psd_consumer.RingBuffer")
@patch("psd_consumer.PSDWorker")
def test_main_flow(mock_worker, mock_rb, mock_est, caplog):
    import psd_consumer
    argv = ["prog", "-f", "2e6", "-s", "2e6", "-w", "1000"]

    with patch("sys.argv", argv):
        with patch("os.read", side_effect=[b"", b""]):  # immediate EOF
            rc = psd_consumer.main()
            assert rc == 0

    mock_est.assert_called_once()
    mock_rb.assert_called_once()
    mock_worker.return_value.start.assert_called_once()


# =============================================================================
# stdin data ingestion
# =============================================================================

def test_main_reads_and_converts_stdin():
    import psd_consumer

    # Prepare fake binary IQ data (int8)
    # I,Q pairs: [(1,2), (3,4), ...]
    raw = bytes([1,2, 3,4, 5,6, 7,8])

    argv = ["prog", "-f", "1e6", "-s", "1e6", "-w", "1000"]
    with patch("sys.argv", argv):
        with patch("os.read", side_effect=[raw, b""], autospec=True):
            fake_rb = MagicMock()
            fake_worker = MagicMock()
            fake_worker.start = MagicMock()

            with patch("psd_consumer.RingBuffer", return_value=fake_rb):
                with patch("psd_consumer.PSDWorker", return_value=fake_worker):
                    rc = psd_consumer.main()
                    assert rc == 0

                    # Ensure write() received complex samples
                    assert fake_rb.write.call_count == 1
                    arr = fake_rb.write.call_args.args[0]
                    assert arr.dtype == np.complex128
                    assert len(arr) == 4
                    assert arr[0] == (1 + 2j)

