import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Test database configuration
# Matches docker-compose.standalone-test.yml credentials
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://test_user:test_password@localhost:5432/test_db"
)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require a real database",
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as requiring a real database"
    )


@pytest.fixture(scope="session")
def test_engine(request):
    """Create a test database engine."""
    # Only create a real engine if we're running integration tests
    if request.config.getoption("--integration"):
        engine = create_engine(TEST_DB_URL)
        return engine
    return None


@pytest.fixture(scope="session", autouse=True)
def init_test_db(test_engine):
    """Initialize the test database schema using PostgreSQLSchemaBuilder."""
    # Only initialize real database if we're running integration tests
    if test_engine:
        from src.axai_pg.utils.schema_builder import PostgreSQLSchemaBuilder

        # Build complete schema with all PostgreSQL features
        # If this fails, the exception will propagate and pytest will show error
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        yield

        # Clean up
        PostgreSQLSchemaBuilder.drop_complete_schema(test_engine)
    else:
        yield


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a new database session for a test with transaction rollback."""
    if not test_engine:
        pytest.skip("Database session only available in integration tests")

    connection = test_engine.connect()
    transaction = connection.begin()
    SessionFactory = sessionmaker(bind=connection)
    session = SessionFactory()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


# Alias for backward compatibility with tests that use real_db_session
@pytest.fixture(scope="function")
def real_db_session(db_session):
    """Alias for db_session for backward compatibility."""
    return db_session


@pytest.fixture(scope="function")
def test_data():
    """Load test data fixtures."""
    return {
        "users": [
            {"username": "user1", "email": "user1@example.com"},
            {"username": "user2", "email": "user2@example.com"},
        ],
        "documents": [
            {"title": "Doc1", "content": "Content1", "org_id": 1},
            {"title": "Doc2", "content": "Content2", "org_id": 1},
        ],
        "topics": [
            {"name": "Topic1", "description": "Description1"},
            {"name": "Topic2", "description": "Description2"},
        ],
    }
