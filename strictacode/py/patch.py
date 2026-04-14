
def radon():
    """
    Monkeypatch radon.cli.FileConfig BEFORE importing radon.cli to avoid
    configparser issues with pyproject.toml files containing '%' in values
    (e.g., pytest log_format with %(levelname)s).
    """
    import sys
    from types import ModuleType
    import os

    # Find the actual radon.cli package location
    import radon
    radon_cli_path = os.path.join(os.path.dirname(radon.__file__), 'cli')

    # Create a mock module for radon.cli that skips __init__.py execution
    mock_cli = ModuleType('radon.cli')
    mock_cli.__path__ = [radon_cli_path]  # Point to real package for submodule imports
    mock_cli.__file__ = os.path.join(radon_cli_path, '__init__.py')

    # Create a no-op FileConfig
    class NoOpFileConfig:
        def get_value(self, _key, _type, default):
            return default

    mock_cli.FileConfig = NoOpFileConfig

    # Install mock BEFORE any imports
    sys.modules['radon.cli'] = mock_cli
