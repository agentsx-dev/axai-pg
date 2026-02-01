"""
Unit test configuration.

NOTE: These tests are named "unit" but actually require a real PostgreSQL database.
They are marked as integration tests and require the --integration flag to run.

To run these tests:
    docker-compose -f docker-compose.standalone-test.yml up -d postgres
    pytest tests/unit/ -v --integration
"""
import pytest

# Mark all tests in this directory as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.db]
