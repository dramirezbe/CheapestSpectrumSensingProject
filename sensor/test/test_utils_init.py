import utils

def test_all_exports_exist():
    """
    Verifica que cada elemento en utils.__all__ 
    exista como atributo del paquete.
    """
    for name in utils.__all__:
        assert hasattr(utils, name), f"utils should expose {name}"
