from typing import Dict, Any
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    window_seconds: int
    max_requests: int


@dataclass
class CacheConfig:
    """Configuration for permission caching."""

    ttl_seconds: int
    max_size: int


@dataclass
class SecurityConfig:
    """Main security configuration class."""

    # Rate limiting configurations per action type
    rate_limits: Dict[str, RateLimitConfig] = None

    # Permission cache configuration
    permission_cache: CacheConfig = None

    # Audit logging configuration
    enable_audit_logging: bool = True
    audit_log_retention_days: int = 30

    def __post_init__(self):
        # Default rate limits if none provided
        if self.rate_limits is None:
            self.rate_limits = {
                "create_document": RateLimitConfig(3600, 100),  # 100 creates per hour
                "update_document": RateLimitConfig(3600, 200),  # 200 updates per hour
                "delete_document": RateLimitConfig(3600, 50),  # 50 deletes per hour
                "create_user": RateLimitConfig(3600, 20),  # 20 user creations per hour
                "export_document": RateLimitConfig(3600, 50),  # 50 exports per hour
            }

        # Default cache configuration if none provided
        if self.permission_cache is None:
            self.permission_cache = CacheConfig(
                ttl_seconds=300,  # 5 minutes
                max_size=1000,  # Maximum number of cached permission sets
            )


class SecurityConfigFactory:
    """Factory for creating environment-specific security configurations."""

    @staticmethod
    def create_development_config() -> SecurityConfig:
        """Create development environment configuration."""
        return SecurityConfig(
            rate_limits={
                "create_document": RateLimitConfig(3600, 1000),
                "update_document": RateLimitConfig(3600, 2000),
                "delete_document": RateLimitConfig(3600, 500),
                "create_user": RateLimitConfig(3600, 100),
                "export_document": RateLimitConfig(3600, 200),
            },
            permission_cache=CacheConfig(
                ttl_seconds=60,  # 1 minute
                max_size=100,  # Smaller cache for development
            ),
            enable_audit_logging=True,
            audit_log_retention_days=7,
        )

    @staticmethod
    def create_production_config() -> SecurityConfig:
        """Create production environment configuration."""
        return SecurityConfig(
            rate_limits={
                "create_document": RateLimitConfig(3600, 100),
                "update_document": RateLimitConfig(3600, 200),
                "delete_document": RateLimitConfig(3600, 50),
                "create_user": RateLimitConfig(3600, 20),
                "export_document": RateLimitConfig(3600, 50),
            },
            permission_cache=CacheConfig(
                ttl_seconds=300,  # 5 minutes
                max_size=1000,  # Larger cache for production
            ),
            enable_audit_logging=True,
            audit_log_retention_days=30,
        )

    @staticmethod
    def create_test_config() -> SecurityConfig:
        """Create test environment configuration."""
        return SecurityConfig(
            rate_limits={
                "create_document": RateLimitConfig(3600, 9999),
                "update_document": RateLimitConfig(3600, 9999),
                "delete_document": RateLimitConfig(3600, 9999),
                "create_user": RateLimitConfig(3600, 9999),
                "export_document": RateLimitConfig(3600, 9999),
            },
            permission_cache=CacheConfig(
                ttl_seconds=1, max_size=10  # 1 second  # Minimal cache for testing
            ),
            enable_audit_logging=False,
            audit_log_retention_days=1,
        )
