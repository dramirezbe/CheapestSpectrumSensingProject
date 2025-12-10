import pytest
from unittest.mock import patch, MagicMock

import main


def test_main_returns_zero():
    """main() debe devolver 0 siempre."""
    assert main.main() == 0


@patch("main.cfg")
@patch("main.sys")
def test___main__block(mock_sys, mock_cfg):
    """
    Testea que el bloque if __name__ == '__main__' llame correctamente a:
    cfg.run_and_capture(main, cfg.LOG_FILES_NUM)
    """
    # Simula run_and_capture devolviendo 123
    mock_cfg.run_and_capture.return_value = 123
    mock_cfg.LOG_FILES_NUM = 5

    # Ejecutamos manualmente el bloque como si fuera __main__
    with patch("main.__name__", "__main__"):
        main.__file__  # acceso para importar correctamente
        from importlib import reload
        reload(main)

    mock_cfg.run_and_capture.assert_called_once_with(main.main, mock_cfg.LOG_FILES_NUM)
    mock_sys.exit.assert_called_once_with(123)
