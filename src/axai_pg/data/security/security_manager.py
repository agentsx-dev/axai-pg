from typing import Optional, Dict, List, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from ..config.database import DatabaseManager
from ..models import User, Organization, Document
from functools import wraps
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityManager:
    _instance: Optional["SecurityManager"] = None
    _permission_cache: Dict[str, Dict[str, List[str]]] = {}

    def __init__(self):
        raise RuntimeError("Use SecurityManager.get_instance()")

    @classmethod
    def get_instance(cls) -> "SecurityManager":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the security manager."""
        self.db = DatabaseManager.get_instance()

    def _get_session(self) -> Session:
        return self.db.get_session()

    def _cache_key(self, user_id: int, org_id: int) -> str:
        return f"{user_id}:{org_id}"

    async def load_permissions(self, user_id: int, org_id: int) -> List[str]:
        """Load and cache user permissions."""
        cache_key = self._cache_key(user_id, org_id)

        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        with self._get_session() as session:
            # Query role_permissions table for user's permissions
            stmt = (
                select(["permission_type"])
                .select_from("role_permissions")
                .where(
                    "role_name IN (SELECT role FROM user_roles WHERE user_id = :user_id)"
                )
            )
            perms = session.execute(stmt, {"user_id": user_id}).fetchall()

            permissions = [p[0] for p in perms]
            self._permission_cache[cache_key] = permissions
            return permissions

    def verify_organization_access(self, user_id: int, org_id: int) -> bool:
        """Verify user belongs to organization."""
        with self._get_session() as session:
            user = session.query(User).filter_by(id=user_id, org_id=org_id).first()
            return user is not None

    def verify_document_access(
        self, user_id: int, doc_id: int, required_permission: str
    ) -> bool:
        """Verify user has access to document."""
        with self._get_session() as session:
            # Check document exists and user has access
            doc = (
                session.query(Document)
                .filter(Document.id == doc_id)
                .join(Organization)
                .filter(
                    (Document.owner_id == user_id) | (Document.org_id == User.org_id)
                )
                .first()
            )

            if not doc:
                return False

            # Check user has required permission
            return required_permission in self.load_permissions(user_id, doc.org_id)

    def log_access(
        self,
        user_id: int,
        action: str,
        resource: str,
        resource_id: Optional[int] = None,
    ):
        """Log access attempts for audit."""
        with self._get_session() as session:
            session.execute(
                """
                INSERT INTO access_log (username, action_type, table_affected, record_id, details)
                VALUES (:username, :action, :resource, :resource_id, :details)
                """,
                {
                    "username": session.query(User.username)
                    .filter_by(id=user_id)
                    .scalar(),
                    "action": action,
                    "resource": resource,
                    "resource_id": resource_id,
                    "details": f"Access at {datetime.utcnow()}",
                },
            )
            session.commit()

    def enforce_rate_limit(
        self, user_id: int, action: str, limit: int, window: int
    ) -> bool:
        """Enforce rate limiting for specific actions."""
        with self._get_session() as session:
            # Count recent actions within window
            count = session.execute(
                """
                SELECT COUNT(*) FROM access_log 
                WHERE username = (SELECT username FROM users WHERE id = :user_id)
                AND action_type = :action
                AND action_time > NOW() - INTERVAL ':window seconds'
                """,
                {"user_id": user_id, "action": action, "window": window},
            ).scalar()

            return count < limit


def require_permission(permission: str):
    """Decorator to enforce permission requirements."""

    def decorator(f):
        @wraps(f)
        async def wrapped(*args, **kwargs):
            security = SecurityManager.get_instance()

            # Extract user_id and org_id from kwargs or first argument (self)
            user_id = kwargs.get("user_id")
            org_id = kwargs.get("org_id")

            if not all([user_id, org_id]):
                if hasattr(args[0], "user_id") and hasattr(args[0], "org_id"):
                    user_id = args[0].user_id
                    org_id = args[0].org_id

            if not security.verify_organization_access(user_id, org_id):
                raise PermissionError("User does not have organization access")

            permissions = await security.load_permissions(user_id, org_id)
            if permission not in permissions:
                raise PermissionError(f"Missing required permission: {permission}")

            start_time = time.time()
            try:
                result = await f(*args, **kwargs)
                security.log_access(user_id, f.__name__, f.__module__, None)
                return result
            except Exception as e:
                logger.error(f"Error in {f.__name__}: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                if duration > 1.0:  # Log slow operations
                    logger.warning(f"Slow operation: {f.__name__} took {duration:.2f}s")

        return wrapped

    return decorator
