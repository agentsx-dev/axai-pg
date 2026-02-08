from typing import Any, Type, TypeVar, Optional, Dict
from .security_manager import SecurityManager, require_permission
from ..repositories.base_repository import BaseRepository

T = TypeVar("T")


class SecureRepository(BaseRepository[T]):
    """Secure repository wrapper that enforces access controls and security patterns."""

    def __init__(self, model_class: Type[T], user_id: int, org_id: int):
        super().__init__(model_class)
        self.user_id = user_id
        self.org_id = org_id
        self.security = SecurityManager.get_instance()

    @require_permission("READ")
    async def find_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID with security checks."""
        if hasattr(self.model_class, "org_id"):
            # Enforce organization isolation
            with self._get_session() as session:
                return (
                    session.query(self.model_class)
                    .filter_by(id=id, org_id=self.org_id)
                    .first()
                )
        return await super().find_by_id(id)

    @require_permission("READ")
    async def find_many(self, filters: Dict[str, Any]) -> list[T]:
        """Get entities matching filters with security checks."""
        if hasattr(self.model_class, "org_id"):
            filters["org_id"] = self.org_id
        return await super().find_many(filters)

    @require_permission("CREATE")
    async def create(self, data: Dict[str, Any]) -> T:
        """Create entity with security checks."""
        if hasattr(self.model_class, "org_id"):
            data["org_id"] = self.org_id
        if hasattr(self.model_class, "owner_id"):
            data["owner_id"] = self.user_id

        # Enforce rate limits for creation
        if not self.security.enforce_rate_limit(
            self.user_id,
            f"create_{self.model_class.__name__.lower()}",
            limit=100,  # Adjust based on requirements
            window=3600,  # 1 hour window
        ):
            raise ValueError("Rate limit exceeded for create operations")

        return await super().create(data)

    @require_permission("UPDATE")
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update entity with security checks."""
        # Verify ownership/access
        entity = await self.find_by_id(id)
        if not entity:
            return None

        if hasattr(entity, "owner_id") and entity.owner_id != self.user_id:
            raise PermissionError("User does not own this resource")

        if hasattr(entity, "org_id") and entity.org_id != self.org_id:
            raise PermissionError("Resource belongs to different organization")

        return await super().update(id, data)

    @require_permission("DELETE")
    async def delete(self, id: int) -> bool:
        """Delete entity with security checks."""
        # Verify ownership/access
        entity = await self.find_by_id(id)
        if not entity:
            return False

        if hasattr(entity, "owner_id") and entity.owner_id != self.user_id:
            raise PermissionError("User does not own this resource")

        if hasattr(entity, "org_id") and entity.org_id != self.org_id:
            raise PermissionError("Resource belongs to different organization")

        return await super().delete(id)

    async def execute_transaction(self, operations: list) -> Any:
        """Execute transaction with security checks for all operations."""
        # Verify permissions for all operations in transaction
        for op in operations:
            if not hasattr(op, "__permission__"):
                raise ValueError("All operations must declare required permissions")

            permission = getattr(op, "__permission__")
            if permission not in await self.security.load_permissions(
                self.user_id, self.org_id
            ):
                raise PermissionError(f"Missing required permission: {permission}")

        return await super().execute_transaction(operations)


def secure_repository(user_id: int, org_id: int):
    """Factory function to create secure repositories."""

    def wrapper(repo_class: Type[BaseRepository]) -> Type[SecureRepository]:
        return lambda model_class: SecureRepository(model_class, user_id, org_id)

    return wrapper
