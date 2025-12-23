import pytest
from axai_pg.data.config.environments import Environments, EnvironmentConfig
from axai_pg.data.config.database import PostgresPoolConfig

def test_development_config():
    """Test development environment configuration."""
    config = Environments.get_development_config()
    assert isinstance(config, EnvironmentConfig)
    assert isinstance(config.pool_config, PostgresPoolConfig)
    
    # Verify development-specific settings
    assert config.pool_config.pool_size == 2
    assert config.pool_config.max_overflow == 2
    assert config.extra_settings["echo"] is True
    assert config.extra_settings["echo_pool"] is True

def test_test_config():
    """Test test environment configuration."""
    config = Environments.get_test_config()
    assert isinstance(config, EnvironmentConfig)
    assert isinstance(config.pool_config, PostgresPoolConfig)
    
    # Verify test-specific settings
    assert config.pool_config.pool_size == 1
    assert config.pool_config.max_overflow == 1
    assert config.extra_settings["echo"] is False
    assert config.pool_config.pool_recycle == 300

def test_production_config():
    """Test production environment configuration."""
    config = Environments.get_production_config()
    assert isinstance(config, EnvironmentConfig)
    assert isinstance(config.pool_config, PostgresPoolConfig)
    
    # Verify production-specific settings
    assert config.pool_config.pool_size == 5
    assert config.pool_config.max_overflow == 5
    assert config.extra_settings["echo"] is False
    assert config.extra_settings["pool_reset_on_return"] == "commit"

def test_environment_selection():
    """Test environment configuration selection."""
    dev_config = Environments.get_config("development")
    test_config = Environments.get_config("test")
    prod_config = Environments.get_config("production")
    
    assert isinstance(dev_config, EnvironmentConfig)
    assert isinstance(test_config, EnvironmentConfig)
    assert isinstance(prod_config, EnvironmentConfig)
    
    # Verify each environment has distinct settings
    assert dev_config != test_config
    assert dev_config != prod_config
    assert test_config != prod_config

def test_invalid_environment():
    """Test handling of invalid environment name."""
    with pytest.raises(ValueError) as exc_info:
        Environments.get_config("invalid_env")
    assert "Unknown environment: invalid_env" in str(exc_info.value)

def test_case_insensitive_environment_names():
    """Test that environment names are case-insensitive."""
    dev_config1 = Environments.get_config("development")
    dev_config2 = Environments.get_config("DEVELOPMENT")
    dev_config3 = Environments.get_config("Development")
    
    assert dev_config1.pool_config == dev_config2.pool_config
    assert dev_config1.pool_config == dev_config3.pool_config
