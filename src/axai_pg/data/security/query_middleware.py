from typing import Optional, Any
from sqlalchemy import event
from sqlalchemy.orm import Session, Query
from .security_manager import SecurityManager
from .security_config import SecurityConfig, SecurityConfigFactory
import logging

logger = logging.getLogger(__name__)


class SecurityQueryMiddleware:
    """Middleware for enforcing security checks on SQLAlchemy queries."""

    def __init__(self, security_config: Optional[SecurityConfig] = None):
        self.security_manager = SecurityManager.get_instance()
        self.config = (
            security_config or SecurityConfigFactory.create_production_config()
        )
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for query interception."""
        event.listen(Session, "before_flush", self._before_flush)
        event.listen(Query, "before_compile", self._before_compile)

    def _before_flush(self, session: Session, flush_context: Any, instances: Any):
        """Handle security checks before database flush."""
        for obj in session.new:
            self._check_create_permission(session, obj)

        for obj in session.dirty:
            self._check_update_permission(session, obj)

        for obj in session.deleted:
            self._check_delete_permission(session, obj)

    def _before_compile(self, query: Query):
        """Handle security checks before query compilation."""
        # Add organization isolation for multi-tenant queries
        self._apply_org_isolation(query)

        # Apply rate limiting if configured
        self._check_rate_limits(query)

    def _check_create_permission(self, session: Session, obj: Any):
        """Check if current user has permission to create object."""
        user_id = self._get_current_user_id(session)
        org_id = self._get_current_org_id(session)

        if not user_id or not org_id:
            raise PermissionError("No authenticated user context")

        resource_name = obj.__tablename__
        if not self._has_permission(user_id, org_id, resource_name, "CREATE"):
            raise PermissionError(f"No CREATE permission for {resource_name}")

        # Set organization ID if model supports it
        if hasattr(obj, "org_id"):
            obj.org_id = org_id

    def _check_update_permission(self, session: Session, obj: Any):
        """Check if current user has permission to update object."""
        user_id = self._get_current_user_id(session)
        org_id = self._get_current_org_id(session)

        if not user_id or not org_id:
            raise PermissionError("No authenticated user context")

        resource_name = obj.__tablename__
        if not self._has_permission(user_id, org_id, resource_name, "UPDATE"):
            raise PermissionError(f"No UPDATE permission for {resource_name}")

        # Verify object belongs to user's organization
        if hasattr(obj, "org_id") and obj.org_id != org_id:
            raise PermissionError("Cannot update object from different organization")

    def _check_delete_permission(self, session: Session, obj: Any):
        """Check if current user has permission to delete object."""
        user_id = self._get_current_user_id(session)
        org_id = self._get_current_org_id(session)

        if not user_id or not org_id:
            raise PermissionError("No authenticated user context")

        resource_name = obj.__tablename__
        if not self._has_permission(user_id, org_id, resource_name, "DELETE"):
            raise PermissionError(f"No DELETE permission for {resource_name}")

        # Verify object belongs to user's organization
        if hasattr(obj, "org_id") and obj.org_id != org_id:
            raise PermissionError("Cannot delete object from different organization")

    def _apply_org_isolation(self, query: Query):
        """Apply organization isolation to queries."""
        session = query.session
        org_id = self._get_current_org_id(session)

        if org_id and query.column_descriptions:
            entity = query.column_descriptions[0]["entity"]
            if hasattr(entity, "org_id"):
                query.filter(entity.org_id == org_id)

    def _check_rate_limits(self, query: Query):
        """Apply rate limiting to queries."""
        session = query.session
        user_id = self._get_current_user_id(session)

        if user_id and query.column_descriptions:
            entity = query.column_descriptions[0]["entity"]
            action_type = f"query_{entity.__tablename__}"

            if action_type in self.config.rate_limits:
                limit_config = self.config.rate_limits[action_type]
                if not self.security_manager.enforce_rate_limit(
                    user_id,
                    action_type,
                    limit_config.max_requests,
                    limit_config.window_seconds,
                ):
                    raise ValueError(f"Rate limit exceeded for {action_type}")

    def _has_permission(
        self, user_id: int, org_id: int, resource: str, permission: str
    ) -> bool:
        """Check if user has specific permission."""
        permissions = self.security_manager.load_permissions(user_id, org_id)
        return permission in permissions

    def _get_current_user_id(self, session: Session) -> Optional[int]:
        """Get current user ID from session info."""
        return getattr(session.info, "user_id", None)

    def _get_current_org_id(self, session: Session) -> Optional[int]:
        """Get current organization ID from session info."""
        return getattr(session.info, "org_id", None)
