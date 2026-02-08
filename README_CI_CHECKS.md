# Running CI Checks Locally

This guide shows you how to run all the same checks locally that GitHub Actions runs, so you can catch issues before pushing.

## Quick Start

Run all CI checks at once:
```bash
./run_ci_checks.sh
```

Or run checks individually (see below).

## What GitHub Actions Runs

The CI workflow (`.github/workflows/ci.yml`) runs these checks in order:

1. **Tests** (`hatch run test`)
2. **Linting** (`hatch run lint:check`) - Black formatting check + Flake8
3. **Type Checking** (`hatch run types:check`) - MyPy

## Running Checks Individually

### 1. Formatting Check (Black)

**Check only** (what CI runs):
```bash
hatch run lint:check
```

**Auto-format** (fixes formatting issues):
```bash
hatch run lint:fmt
```

### 2. Type Checking (MyPy)

```bash
hatch run types:check
```

### 3. Tests

**Prerequisites:** PostgreSQL must be running
```bash
# Start PostgreSQL (if not already running)
docker-compose -f docker-compose.standalone-test.yml up -d postgres

# Run tests
hatch run test
```

Or use the test script:
```bash
./run_tests.sh
```

## Complete CI Workflow Locally

To run everything exactly as CI does:

```bash
# 1. Ensure PostgreSQL is running
docker-compose -f docker-compose.standalone-test.yml up -d postgres

# 2. Set environment variables (matching CI)
export TEST_DATABASE_URL="postgresql://test_user:test_password@localhost:5432/test_db"
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=test_db
export POSTGRES_USER=test_user
export POSTGRES_PASSWORD=test_password
export POSTGRES_SCHEMA=public

# 3. Run all checks
hatch run test              # Tests
hatch run lint:check        # Formatting + linting
hatch run types:check       # Type checking
```

Or use the convenience script:
```bash
./run_ci_checks.sh
```

## Pre-commit Hooks (Optional)

If you want checks to run automatically before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# Run on all files (first time)
pre-commit run --all-files
```

This will run Black, Flake8, and MyPy automatically before commits.

## Troubleshooting

### "hatch: command not found"
Install hatch:
```bash
pip install hatch
```

### Formatting issues
If `hatch run lint:check` fails, auto-format with:
```bash
hatch run lint:fmt
```

### PostgreSQL connection errors
Make sure PostgreSQL is running:
```bash
docker-compose -f docker-compose.standalone-test.yml up -d postgres
```

### MyPy errors
MyPy type checking can be strict. Check the specific errors and fix type hints or add `# type: ignore` comments if needed.

## Summary

| Check | Command | Auto-fix |
|-------|---------|----------|
| Formatting | `hatch run lint:check` | `hatch run lint:fmt` |
| Linting | `hatch run lint:check` | Manual fixes |
| Type checking | `hatch run types:check` | Manual fixes |
| Tests | `hatch run test` | N/A |
| **All checks** | `./run_ci_checks.sh` | Formatting only |
