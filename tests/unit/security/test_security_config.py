import pytest
from datetime import timedelta
from axai_pg.data.security.security_config import (
    SecurityConfig,
    SecurityConfigFactory,
    RateLimitConfig,
    CacheConfig,
)


def test_default_security_config():
    """Test default security configuration creation."""
    config = SecurityConfig()

    # Test default rate limits
    assert "create_document" in config.rate_limits
    assert config.rate_limits["create_document"].max_requests == 100
    assert config.rate_limits["create_document"].window_seconds == 3600

    # Test default cache config
    assert config.permission_cache.ttl_seconds == 300
    assert config.permission_cache.max_size == 1000

    # Test default audit settings
    assert config.enable_audit_logging is True
    assert config.audit_log_retention_days == 30


def test_development_config():
    """Test development environment configuration."""
    config = SecurityConfigFactory.create_development_config()

    # Verify development-specific settings
    assert config.rate_limits["create_document"].max_requests == 1000
    assert config.permission_cache.ttl_seconds == 60
    assert config.permission_cache.max_size == 100
    assert config.audit_log_retention_days == 7


def test_production_config():
    """Test production environment configuration."""
    config = SecurityConfigFactory.create_production_config()

    # Verify production-specific settings
    assert config.rate_limits["create_document"].max_requests == 100
    assert config.permission_cache.ttl_seconds == 300
    assert config.permission_cache.max_size == 1000
    assert config.audit_log_retention_days == 30


def test_test_config():
    """Test test environment configuration."""
    config = SecurityConfigFactory.create_test_config()

    # Verify test-specific settings
    assert config.rate_limits["create_document"].max_requests == 9999
    assert config.permission_cache.ttl_seconds == 1
    assert config.permission_cache.max_size == 10
    assert config.enable_audit_logging is False
    assert config.audit_log_retention_days == 1


def test_custom_rate_limits():
    """Test custom rate limit configuration."""
    custom_rate_limits = {
        "custom_action": RateLimitConfig(1800, 50)  # 50 requests per 30 minutes
    }
    config = SecurityConfig(rate_limits=custom_rate_limits)

    assert "custom_action" in config.rate_limits
    assert config.rate_limits["custom_action"].window_seconds == 1800
    assert config.rate_limits["custom_action"].max_requests == 50


def test_custom_cache_config():
    """Test custom cache configuration."""
    custom_cache = CacheConfig(ttl_seconds=600, max_size=2000)
    config = SecurityConfig(permission_cache=custom_cache)

    assert config.permission_cache.ttl_seconds == 600
    assert config.permission_cache.max_size == 2000


def test_rate_limit_creation():
    """Test rate limit configuration creation."""
    # Test valid configuration
    rate_limit = RateLimitConfig(3600, 100)
    assert rate_limit.window_seconds == 3600
    assert rate_limit.max_requests == 100

    # Test that dataclass accepts any values (no built-in validation)
    rate_limit_custom = RateLimitConfig(1800, 50)
    assert rate_limit_custom.window_seconds == 1800
    assert rate_limit_custom.max_requests == 50


def test_cache_config_creation():
    """Test cache configuration creation."""
    # Test valid configuration
    cache_config = CacheConfig(300, 1000)
    assert cache_config.ttl_seconds == 300
    assert cache_config.max_size == 1000

    # Test that dataclass accepts any values (no built-in validation)
    cache_config_custom = CacheConfig(600, 2000)
    assert cache_config_custom.ttl_seconds == 600
    assert cache_config_custom.max_size == 2000
