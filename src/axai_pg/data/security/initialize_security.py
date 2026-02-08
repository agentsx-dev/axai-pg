from sqlalchemy.orm import Session
from ..config.database import DatabaseManager
from ..models.security import UserRole, RolePermission
from ..models import User


def create_default_permissions(session: Session) -> None:
    """Create default role permissions if they don't exist."""
    default_permissions = [
        # Admin permissions
        ("admin", "documents", "READ"),
        ("admin", "documents", "CREATE"),
        ("admin", "documents", "UPDATE"),
        ("admin", "documents", "DELETE"),
        ("admin", "users", "READ"),
        ("admin", "users", "CREATE"),
        ("admin", "users", "UPDATE"),
        ("admin", "users", "DELETE"),
        ("admin", "organizations", "READ"),
        ("admin", "organizations", "UPDATE"),
        # User permissions
        ("user", "documents", "READ"),
        ("user", "documents", "CREATE"),
        ("user", "documents", "UPDATE"),
        ("user", "documents", "DELETE"),
        ("user", "users", "READ"),
        # Readonly permissions
        ("readonly", "documents", "READ"),
        ("readonly", "users", "READ"),
    ]

    for role, resource, permission in default_permissions:
        # Check if permission already exists
        existing = (
            session.query(RolePermission)
            .filter_by(
                role_name=role, resource_name=resource, permission_type=permission
            )
            .first()
        )

        if not existing:
            perm = RolePermission(
                role_name=role, resource_name=resource, permission_type=permission
            )
            session.add(perm)


def create_admin_user(session: Session) -> None:
    """Create default admin user if it doesn't exist."""
    admin = session.query(User).filter_by(username="admin").first()

    if not admin:
        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            org_id=1,  # Assumes default organization exists
        )
        session.add(admin)
        session.flush()  # Flush to get admin.id

        # Assign admin role
        admin_role = UserRole(user_id=admin.id, role_name="admin")
        session.add(admin_role)


def initialize_security() -> None:
    """Initialize all security-related default data."""
    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        create_default_permissions(session)
        create_admin_user(session)
        session.commit()


if __name__ == "__main__":
    initialize_security()
