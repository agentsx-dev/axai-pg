# Contributing to AXAI PostgreSQL Models

Thank you for your interest in contributing to the AXAI PostgreSQL Models project! This document provides guidelines and best practices for contributing.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Best Practices](#best-practices)

## Getting Started

### Prerequisites

- Python >= 3.10
- PostgreSQL 12 or later
- Docker and Docker Compose (for testing)
- Git

### Setup Development Environment

1. **Clone the repository**:
```bash
git clone <repository-url>
cd axai-pg
```

2. **Install dependencies**:
```bash
# Install in editable mode with development extras
pip install -e ".[dev]"

# Or use Hatch (recommended)
pip install hatch
hatch env create
```

3. **Install pre-commit hooks** (optional but recommended):
```bash
pre-commit install
```

4. **Start test database**:
```bash
docker-compose -f docker-compose.standalone-test.yml up -d
```

5. **Verify setup**:
```bash
pytest tests/integration/ -v --integration
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test additions or modifications

### 2. Make Changes

- Follow the [Code Style](#code-style) guidelines
- Write or update tests for your changes
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run all tests
pytest tests/integration/ -v --integration

# Run specific test file
pytest tests/integration/test_schema_creation.py -v --integration

# Run with coverage
pytest tests/ -v --integration --cov=src --cov-report=term-missing
```

### 4. Format and Lint

```bash
# Using Hatch (recommended)
hatch run lint:check    # Check formatting and linting
hatch run lint:fmt      # Auto-format code
hatch run types:check   # Type checking

# Or manually
black src/ tests/       # Format code
flake8 src/ tests/      # Check linting
mypy src/               # Type checking
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "Brief description of changes"
```

Commit message format:
```
type: Brief description (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Include the motivation for the change and contrast with
previous behavior.

- Bullet points are okay
- Use a hyphen followed by a space

Refs: #issue-number
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

## Code Style

### Python

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://github.com/psf/black) for code formatting (line length: 88)
- Use type hints where appropriate
- Write docstrings for all public functions and classes (Google style)

Example:
```python
from typing import Optional
from sqlalchemy.orm import Session

def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """
    Retrieve a user by their email address.

    Args:
        session: SQLAlchemy database session
        email: User's email address

    Returns:
        User object if found, None otherwise

    Raises:
        ValueError: If email format is invalid
    """
    # Implementation
    pass
```

### SQLAlchemy Models

- Models are the single source of truth for schema
- Include docstrings explaining the model's purpose
- Use proper constraints (CHECK, UNIQUE, NOT NULL)
- Define indexes for frequently queried columns
- Use relationships with appropriate lazy loading

Example:
```python
class Document(Base):
    """
    Documents store content and metadata for the document management system.

    Each document belongs to an organization (multi-tenant) and is owned
    by a user. Documents support versioning, topics, and summaries.
    """
    __tablename__ = 'documents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    # ... more fields

    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="documents_title_not_empty"),
        Index('idx_documents_org_id', 'org_id'),
    )
```

### Repository Pattern

- All database access goes through repositories
- Use `@track_metrics` decorator for monitoring
- Implement proper transaction management
- Add docstrings with usage examples

## Testing

### Philosophy

**All tests use real PostgreSQL databases.** No mocking of database operations.

Why?
- Validates actual PostgreSQL behavior
- Tests constraints, triggers, and indexes
- Catches schema compatibility issues
- Ensures query performance

### Writing Tests

1. **Use proper fixtures**:
```python
def test_create_user(db_session):
    """Test user creation with organization."""
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.flush()

    user = User(
        username="testuser",
        email="test@example.com",
        org_id=org.id
    )
    db_session.add(user)
    db_session.commit()

    assert db_session.query(User).filter_by(username="testuser").first() is not None
```

2. **Use proper markers**:
```python
@pytest.mark.integration
@pytest.mark.db
def test_database_operation(db_session):
    # Test implementation
    pass
```

3. **Test isolation**:
Each test runs in a transaction that is automatically rolled back, ensuring tests don't affect each other.

4. **Test naming**:
- Use descriptive names: `test_create_user_with_valid_email`
- Group related tests in classes
- Add docstrings explaining what's being tested

### Test Coverage

Aim for high test coverage of:
- Model constraints and relationships
- Repository methods
- Schema creation and validation
- Transaction behavior
- Multi-tenant isolation
- Error handling

## Submitting Changes

### Before Submitting

- [ ] All tests pass
- [ ] Code is formatted (black)
- [ ] No linting errors (flake8)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for user-facing changes)
- [ ] Commit messages follow convention

### Pull Request Process

1. **Push your branch**:
```bash
git push origin feature/your-feature-name
```

2. **Create Pull Request**:
- Use a clear, descriptive title
- Provide detailed description of changes
- Reference related issues
- Include screenshots for UI changes (if applicable)

3. **PR Description Template**:
```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

4. **Review Process**:
- Address reviewer feedback
- Keep the PR up to date with main branch
- Ensure CI passes

## Best Practices

### Database Changes

1. **Model Changes**:
   - Update SQLAlchemy model first
   - Schema is automatically generated from models
   - Add appropriate constraints and indexes
   - Update tests to verify new schema

2. **Performance**:
   - Add indexes for foreign keys and frequently queried columns
   - Use eager loading for related objects when appropriate
   - Monitor query performance with repository metrics

3. **Multi-Tenancy**:
   - Always include `org_id` for tenant-specific data
   - Test data isolation between organizations
   - Use query middleware for automatic filtering

### Repository Pattern

1. **Transaction Management**:
```python
from axai_pg import DatabaseManager

db = DatabaseManager.get_instance()

with db.session_scope() as session:
    # Operations here
    # Automatic commit on success, rollback on exception
    pass
```

2. **Error Handling**:
```python
try:
    with db.session_scope() as session:
        # Database operations
        pass
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # Handle error appropriately
```

### Documentation

- Update CLAUDE.md for development workflow changes
- Update README.md for user-facing changes
- Add docstrings to all public APIs
- Include usage examples in docstrings
- Update CHANGELOG.md for each release

### Security

- Never commit credentials or secrets
- Use environment variables for configuration
- Validate and sanitize all inputs
- Follow principle of least privilege
- Test multi-tenant data isolation

## Getting Help

- Check [CLAUDE.md](CLAUDE.md) for project overview and common commands
- Review [docs/](docs/) for detailed documentation
- Look at existing code for examples
- Ask questions in Pull Requests or Issues

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Welcome newcomers and help them learn
- Follow the project's technical direction

Thank you for contributing! 🎉
