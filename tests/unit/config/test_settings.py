import pytest
from axai_pg.data.config.settings import Settings


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    env_vars = {
        "APP_ENV": "test",
        "POSTGRES_HOST": "test-host",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test-db",
        "POSTGRES_USER": "test-user",
        "POSTGRES_PASSWORD": "test-pass",
        "POSTGRES_SCHEMA": "public",
        "POSTGRES_SSL_MODE": "prefer",
        "DEBUG": "false",
        "LOG_SQL": "false",
        "DB_CONNECTION_TIMEOUT": "30",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


def test_settings_singleton(mock_env_vars):
    """Test that Settings maintains singleton pattern."""
    settings1 = Settings.get()
    settings2 = Settings.get()
    assert settings1 is settings2

    # Test reload creates new instance
    settings3 = Settings.reload()
    assert settings1 is not settings3


def test_load_from_env(mock_env_vars):
    """Test loading settings from environment variables."""
    settings = Settings.load()

    assert settings.environment == "test"
    assert settings.conn_config.host == "test-host"
    assert settings.conn_config.database == "test-db"
    assert not settings.debug_mode
    assert not settings.log_sql
    assert settings.connection_timeout == 30


def test_missing_required_env_vars(monkeypatch):
    """Test handling of missing required environment variables."""
    # Clear all environment variables
    for var in ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError) as exc_info:
        Settings.reload()
    assert "Required environment variable" in str(exc_info.value)


def test_invalid_environment(mock_env_vars, monkeypatch):
    """Test handling of invalid environment name."""
    monkeypatch.setenv("APP_ENV", "invalid")

    with pytest.raises(ValueError) as exc_info:
        Settings.reload()
    assert "Invalid environment: invalid" in str(exc_info.value)


def test_validation(mock_env_vars):
    """Test settings validation."""
    settings = Settings.get()
    settings.validate()  # Should not raise any exceptions

    # Test invalid pool size
    settings.env_config.pool_config.pool_size = 0
    with pytest.raises(ValueError) as exc_info:
        settings.validate()
    assert "Pool size must be at least 1" in str(exc_info.value)

    # Reset pool size and test invalid timeout
    settings = Settings.reload()
    settings.connection_timeout = 0
    with pytest.raises(ValueError) as exc_info:
        settings.validate()
    assert "Connection timeout must be positive" in str(exc_info.value)


def test_engine_settings(mock_env_vars):
    """Test generation of SQLAlchemy engine settings."""
    settings = Settings.get()
    engine_settings = settings.get_engine_settings()

    assert isinstance(engine_settings, dict)
    assert "pool_size" in engine_settings
    assert "max_overflow" in engine_settings
    assert "pool_timeout" in engine_settings
    assert "connect_args" in engine_settings
    assert "connect_timeout" in engine_settings["connect_args"]
    assert "sslmode" in engine_settings["connect_args"]


def test_different_environments(mock_env_vars, monkeypatch):
    """Test settings across different environments."""
    # Test development environment
    monkeypatch.setenv("APP_ENV", "development")
    dev_settings = Settings.reload()
    assert dev_settings.environment == "development"
    assert dev_settings.env_config.pool_config.pool_size == 2

    # Test production environment
    monkeypatch.setenv("APP_ENV", "production")
    prod_settings = Settings.reload()
    assert prod_settings.environment == "production"
    assert prod_settings.env_config.pool_config.pool_size == 5


def test_debug_and_logging_flags(mock_env_vars, monkeypatch):
    """Test debug and logging configuration."""
    # Test debug mode - use development environment where echo=True in extra_settings
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_SQL", "true")
    settings = Settings.reload()

    assert settings.debug_mode is True
    assert settings.log_sql is True

    # Verify engine settings reflect logging configuration
    # Note: extra_settings from environment config may override log_sql value
    # Development environment has echo=True in extra_settings
    engine_settings = settings.get_engine_settings()
    assert engine_settings["echo"] is True
