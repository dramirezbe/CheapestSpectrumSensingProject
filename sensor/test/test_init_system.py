import pytest
from unittest.mock import patch, MagicMock

import init_system


# =============================================================================
# Test main()
# =============================================================================

def test_init_system_main_logs_and_returns_zero():
    """main() debe escribir dos warnings y devolver 0."""
    mock_logger = MagicMock()
    
    # patch logger dentro del módulo
    with patch("init_system.log", mock_logger):
        rc = init_system.main()

    assert rc == 0
    # Check that two warnings are logged
    assert mock_logger.warning.call_count == 2
    mock_logger.warning.assert_any_call("Module init_system running...")
    mock_logger.warning.assert_any_call("Module init_system finished...")


# =============================================================================
# Test del bloque "__main__"
# =============================================================================

@patch("init_system.cfg")
@patch("init_system.sys")
def test_init_system_entrypoint(mock_sys, mock_cfg):
    """
    Testea que al ejecutarse como __main__, se llame:
      cfg.run_and_capture(main, cfg.LOG_FILES_NUM)
      sys.exit(rc)
    """
    mock_cfg.LOG_FILES_NUM = 5
    mock_cfg.run_and_capture.return_value = 123

    # Forzamos que init_system.__name__ == "__main__" y recargamos el módulo
    with patch("init_system.__name__", "__main__"):
        from importlib import reload
        reload(init_system)

    mock_cfg.run_and_capture.assert_called_once_with(init_system.main, mock_cfg.LOG_FILES_NUM)
    mock_sys.exit.assert_called_once_with(123)
