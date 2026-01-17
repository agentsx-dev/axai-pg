# AXAI PostgreSQL Models

This package provides PostgreSQL models and database management for AXAI applications. It includes a comprehensive set of models for managing organizations, users, documents, topics, and their relationships.

## Installation

### For Production Use

```bash
pip install axai-pg
```

### For Development

```bash
# Clone the repository
git clone <repository-url>
cd axai-pg

# Install in editable mode with all dev dependencies
pip install -e ".[dev]"

# Or install with just testing extras
pip install -e ".[testing]"

# Using Hatch (recommended for contributors)
pip install hatch
hatch env create  # Create default environment
```

### Prerequisites

- Python >=3.10
- PostgreSQL 12 or later
- Docker and Docker Compose (for running tests)

## Usage

### Basic Setup

```python
from axai_pg import DatabaseManager, PostgresConnectionConfig
from axai_pg import Organization, User, Document, Summary, Topic

# Initialize the database connection
conn_config = PostgresConnectionConfig(
    host="localhost",  # or "postgres" if in same docker network
    port=5432,
    database="your_db",
    username="your_user",
    password="your_password"
)
DatabaseManager.initialize(conn_config)

# Get a database session
db = DatabaseManager.get_instance()
```

### Creating and Managing Data

```python
# Create an organization and a user
with db.session_scope() as session:
    # Create an organization
    org = Organization(name="Test Organization")
    session.add(org)
    session.flush()  # This gets us the org.id
    
    # Create a user in that organization
    user = User(
        username="testuser",
        email="test@example.com",
        org_id=org.id
    )
    session.add(user)
    session.flush()  # This gets us the user.id
    
    # Create a document
    document = Document(
        title="Test Document",
        content="This is a test document content",
        owner_id=user.id,
        org_id=org.id,
        document_type="text",
        status="draft"
    )
    session.add(document)
    session.flush()  # This gets us the document.id
    
    # Create a summary for the document
    summary = Summary(
        document_id=document.id,
        content="This is a summary of the test document",
        summary_type="abstract",
        tool_agent="test-agent",
        confidence_score=0.95
    )
    session.add(summary)
    
    # Create a topic
    topic = Topic(
        name="Test Topic",
        description="A test topic",
        keywords=["test", "example"],
        extraction_method="manual",
        global_importance=0.8
    )
    session.add(topic)
    
    # The session will automatically commit when the context manager exits
```

### Querying Data

```python
with db.session_scope() as session:
    # Get all organizations
    organizations = session.query(Organization).all()
    
    # Get a specific user
    user = session.query(User).filter_by(username="testuser").first()
    
    # Get all documents for an organization
    org_documents = session.query(Document).filter_by(org_id=org.id).all()
    
    # Get documents with their summaries
    documents_with_summaries = (
        session.query(Document, Summary)
        .join(Summary)
        .filter(Document.org_id == org.id)
        .all()
    )
```

### Using in FastAPI Applications

```python
from fastapi import FastAPI, Depends
from axai_pg import DatabaseManager, PostgresConnectionConfig
from axai_pg import Organization, User

app = FastAPI()

# Database dependency
def get_db():
    db = DatabaseManager.get_instance()
    with db.session_scope() as session:
        yield session

@app.post("/organizations/")
async def create_organization(org: dict, session = Depends(get_db)):
    organization = Organization(name=org["name"])
    session.add(organization)
    session.flush()
    return {"id": organization.id, "name": organization.name}

@app.get("/users/{user_id}")
async def get_user(user_id: int, session = Depends(get_db)):
    user = session.query(User).filter_by(id=user_id).first()
    return user
```

### Using in Django Applications

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# views.py
from django.http import JsonResponse
from axai_pg import DatabaseManager, PostgresConnectionConfig
from axai_pg import Organization, User

def create_organization(request):
    db = DatabaseManager.get_instance()
    with db.session_scope() as session:
        org = Organization(name=request.POST['name'])
        session.add(org)
        session.flush()
        return JsonResponse({'id': org.id, 'name': org.name})
```

## Models

The package includes the following models:

### Core Models
- **Organization**: Represents B2B tenants in the multi-tenant system
- **User**: Users belonging to organizations
- **Document**: Core document storage with ownership and metadata
- **DocumentVersion**: Historical versions of documents

### Content Analysis
- **Summary**: Document summaries generated by various tools/agents
- **Topic**: Topics extracted from document content
- **DocumentTopic**: Junction table linking documents to topics
- **Feedback**: User feedback records

### Graph Models
- **GraphEntity**: Nodes for the graph representation of document connections
- **GraphRelationship**: Relationships between nodes in the document graph

### Collection Models
- **Collection**: Document collections with hierarchical support
- **CollectionEntity**: Entities within collections
- **CollectionRelationship**: Relationships within collections
- **VisibilityProfile**: Visibility settings for collections

### Security Models
- **Role**: User roles for access control
- **UserRole**: Junction table linking users to roles
- **RolePermission**: Permissions assigned to roles
- **AuditLog**: Audit trail for security events
- **Token**: Authentication tokens (JWT)

## Development

### Setup

To install the package in development mode:

```bash
git clone https://github.com/your-org/axai-pg.git
cd axai-pg

# Option 1: Using pip
pip install -e ".[dev]"

# Option 2: Using Hatch (recommended for contributors)
pip install hatch
hatch env create
```

### Running Tests

```bash
# Using the test script (recommended)
./run_tests.sh

# Using Hatch
hatch run test          # Run integration tests
hatch run test-all      # Run all tests

# Using pytest directly
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/integration/ -v --integration
```

### Code Quality

```bash
# Format code
hatch run lint:fmt      # Auto-format with black

# Check formatting and linting
hatch run lint:check    # Check black and flake8

# Type checking
hatch run types:check   # Run mypy
```

### Building

```bash
# Build package
hatch build

# Install locally
pip install -e .
```

## Testing

**All tests require a real PostgreSQL database** - there are no mock-based unit tests. The database schema is created programmatically using SQLAlchemy models with PostgreSQL-specific features (triggers, check constraints, indexes, etc.).

> **Note:** Tests in `tests/unit/` are named "unit" but actually require a database connection and are automatically marked as integration tests.

### Quick Start

1. **Install dependencies**:
```bash
pip install -e ".[dev]"
```

2. **Start the test database**:
```bash
docker-compose -f docker-compose.standalone-test.yml up -d
```

3. **Run the tests**:
```bash
# Using the test script (easiest)
./run_tests.sh

# Using Hatch
hatch run test          # Run integration tests with coverage
hatch run test-all      # Run all tests

# Using pytest directly - run ALL tests
pytest tests/ -v --integration

# Run only core integration tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/integration/ -v --integration

# Run specific test file
pytest tests/integration/test_schema_creation.py -v --integration
```

4. **Clean up**:
```bash
docker-compose -f docker-compose.standalone-test.yml down -v
```

### Test Database Configuration

The test database uses the following credentials (from `docker-compose.standalone-test.yml`):
- **Host**: localhost
- **Port**: 5432
- **Database**: test_db
- **Username**: test_user
- **Password**: test_password

These match the defaults in `tests/conftest.py`. You can override by setting the `TEST_DATABASE_URL` environment variable:

```bash
export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/my_test_db"
pytest tests/integration/ -v --integration
```

### SQLAlchemy-First Schema Approach

The project uses **SQLAlchemy models as the single source of truth** for schema definition. The schema is created programmatically via `PostgreSQLSchemaBuilder`, which:

1. Creates PostgreSQL extensions (uuid-ossp)
2. Creates custom trigger functions (auto-update timestamps)
3. Creates tables from SQLAlchemy models (`Base.metadata.create_all`)
4. Creates triggers for each table
5. Adds table comments
6. Creates performance indexes

Schema is managed exclusively through SQLAlchemy models.

### Test Organization

All tests are integration tests using real PostgreSQL:

- **`tests/integration/test_schema_creation.py`**: Comprehensive schema validation (16 tests)
  - Tables, extensions, triggers, constraints, indexes, foreign keys, JSONB columns
- **`tests/integration/test_schema_builder.py`**: PostgreSQLSchemaBuilder testing (10 tests)
  - Build schema, idempotency, individual component testing
- **`tests/integration/test_database_initializer.py`**: Database lifecycle (8 tests)
  - Setup, teardown, context managers, DatabaseManager integration
- **`tests/integration/test_crud_operations.py`**: CRUD operations (6 tests)
  - Create, read, update operations for all models
- **`tests/conftest.py`**: Test fixtures and database setup

### Test Fixtures

- **`test_engine`**: Session-scoped SQLAlchemy engine
- **`db_session`**: Function-scoped session with automatic transaction rollback
- **`real_db_session`**: Alias for `db_session` (backward compatibility)
- **`test_data`**: Sample data fixtures

### Writing Tests

```python
@pytest.mark.integration
def test_something(db_session):
    # Create test data
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.flush()

    user = User(username="testuser", email="test@example.com", org_id=org.id)
    db_session.add(user)
    db_session.commit()

    # Query the database
    result = db_session.query(User).filter_by(username="testuser").first()
    assert result is not None
    assert result.email == "test@example.com"
    assert result.org_id == org.id
```

### Database Reset

For development and testing purposes, you can use the `DatabaseInitializer` utility to reset the database:

```python
from axai_pg.utils import DatabaseInitializer, DatabaseInitializerConfig
from axai_pg.data.config.database import PostgresConnectionConfig

config = DatabaseInitializerConfig(
    connection_config=PostgresConnectionConfig.from_env(),
    auto_create_db=True
)

db_init = DatabaseInitializer(config)
db_init.reset_database()  # Drops and recreates database with schema
```

Or use the test fixtures for pytest-based workflows (see "Integration Testing with Other Systems" section).

## Integration Testing with Other Systems

The axai-pg package provides utilities to simplify integration testing for external systems that use this package.

### Quick Start for External Systems

1. **Install with testing extras**:
```bash
pip install axai-pg[testing]
```

2. **Start the test database**:
```bash
docker-compose -f docker-compose.standalone-test.yml up -d
```

3. **Use pytest fixtures in your tests**:
```python
from axai_pg.testing.fixtures import axai_db_session
from axai_pg.data.models import Organization, User

def test_my_feature(axai_db_session):
    # Create test data
    org = Organization(name="Test Org")
    axai_db_session.add(org)
    axai_db_session.commit()

    # Run your tests
    assert axai_db_session.query(Organization).count() == 1
    # Session automatically rolls back after test
```

### Programmatic Database Initialization

For non-pytest scenarios or custom test setups:

```python
from axai_pg.utils import DatabaseInitializer, DatabaseInitializerConfig
from axai_pg.data.config.database import PostgresConnectionConfig

# Configure database
conn_config = PostgresConnectionConfig(
    host='localhost',
    port=5432,
    database='test_db',
    username='test_user',
    password='test_password'
)

config = DatabaseInitializerConfig(
    connection_config=conn_config,
    auto_create_db=True,
    auto_drop_on_exit=True  # Automatic cleanup
)

# Use context manager for automatic setup/teardown
with DatabaseInitializer(config) as db_init:
    db_init.setup_database()

    # Run your tests
    with db_init.session_scope() as session:
        # Perform database operations
        pass

# Database is automatically cleaned up
```

### Available Pytest Fixtures

- **`axai_db_config`**: Connection configuration
- **`axai_test_db`**: Session-scoped database initialization
- **`axai_db_session`**: Function-scoped session with automatic rollback
- **`axai_db_manager`**: Direct access to DatabaseManager
- **`axai_clean_db_session`**: Session without rollback (commits changes)
- **`axai_reset_db`**: Reset database to clean state

### Environment Variables

Configure the test database using environment variables:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=test_db
export POSTGRES_USER=test_user
export POSTGRES_PASSWORD=test_password

# Optional: Auto-drop database after tests
export AXAI_AUTO_DROP_DB=true

# Optional: Load sample data
export AXAI_LOAD_SAMPLE_DATA=true
```

### Docker Compose for CI/CD

The `docker-compose.standalone-test.yml` file provides a minimal PostgreSQL setup perfect for CI/CD pipelines:

```yaml
# In your CI configuration
services:
  test:
    image: python:3.12
    depends_on:
      - postgres
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    command: pytest tests/

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
```

### Examples

See the `examples/` directory for comprehensive usage examples:
- `integration_test_example.py` - Multiple integration testing patterns
- `production_init_example.py` - Production database initialization

For more details, see the [Database Initializer documentation](#database-initialization).

## Database Initialization

The `DatabaseInitializer` utility can be used for both testing and production scenarios.

### Features

- **Database lifecycle management**: Create, setup, teardown databases
- **Schema management**: Apply SQL schema files
- **Sample data loading**: Load test data from scripts
- **Health checks**: Verify database connectivity
- **Context manager support**: Automatic cleanup
- **Production-ready**: Environment-specific configurations

### Use Cases

1. **Integration Testing**: Setup/teardown test databases
2. **Development**: Initialize development databases with sample data
3. **Production Deployment**: Initial database setup
4. **Blue-Green Deployments**: Prepare new database instances
5. **Health Checks**: Kubernetes readiness/liveness probes

### Basic Usage

```python
from axai_pg.utils import DatabaseInitializer, DatabaseInitializerConfig
from axai_pg.data.config.database import PostgresConnectionConfig

# Configure
config = DatabaseInitializerConfig(
    connection_config=PostgresConnectionConfig.from_env(),
    auto_create_db=True,
    auto_drop_on_exit=False  # Set True for tests
)

# Initialize
db_init = DatabaseInitializer(config)
db_init.setup_database(load_sample_data=False)

# Use database
db_manager = db_init.get_database_manager()
with db_manager.session_scope() as session:
    # Perform operations
    pass

# Cleanup when done
db_init.teardown_database()
```

## Project Structure

```
axai-pg/
├── CHANGELOG.md          # Version history and changes
├── CLAUDE.md             # Claude Code instructions
├── README.md             # This file
├── docs/
│   ├── operations/       # Database usage documentation
│   │   ├── db_usage_guide.md
│   │   └── backup_recovery.md
│   └── schema/           # Schema documentation
│       ├── schema_readme.md
│       └── entity_diagram.md
├── src/axai_pg/
│   ├── data/
│   │   ├── config/       # Database configuration
│   │   ├── models/       # SQLAlchemy models (single source of truth)
│   │   ├── repositories/ # Repository pattern implementations
│   │   └── security/     # Security and multi-tenancy
│   ├── utils/            # Utilities (schema builder, initializer)
│   └── testing/          # Test fixtures for external systems
├── tests/
│   ├── integration/      # Integration tests (real PostgreSQL)
│   ├── unit/             # Unit tests
│   └── conftest.py       # Pytest configuration and fixtures
└── examples/             # Usage examples
```

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[CLAUDE.md](CLAUDE.md)** - Project overview and development guidelines
- **[docs/operations/db_usage_guide.md](docs/operations/db_usage_guide.md)** - Database usage patterns and best practices
- **[docs/schema/](docs/schema/)** - Schema design and relationships
- **[docs/integration_spec.md](docs/integration_spec.md)** - External system integration guide

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

See [CLAUDE.md](CLAUDE.md) for development guidelines and common commands.

## License

MIT
