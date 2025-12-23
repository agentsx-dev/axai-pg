import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text
from axai_pg.data.config.database import DatabaseManager, PostgresConnectionConfig, PostgresPoolConfig
from axai_pg.data.config.environments import Environments

@pytest.fixture(scope="module")
def db_manager():
    """Setup database manager with test configuration."""
    config = Environments.get_test_config()
    conn_config = PostgresConnectionConfig.from_env()
    DatabaseManager.initialize(conn_config, config.pool_config)
    return DatabaseManager.get_instance()

def test_concurrent_connections(db_manager):
    """Test handling of multiple concurrent database connections."""
    def run_query(i):
        with db_manager.session_scope() as session:
            # Simulate some work
            time.sleep(0.1)
            result = session.execute(text("SELECT pg_sleep(0.1)")).scalar()
            return i, result is not None

    # Test with 10 concurrent connections
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_query, range(10)))
    
    # Verify all operations completed successfully
    assert all(success for _, success in results)
    assert len(results) == 10

def test_connection_pool_scaling(db_manager):
    """Test connection pool behavior under load."""
    def get_pool_stats():
        return {
            "size": db_manager.engine.pool.size(),
            "overflow": db_manager.engine.pool.overflow(),
            "checkedout": db_manager.engine.pool.checkedout()
        }

    initial_stats = get_pool_stats()
    
    def run_query():
        with db_manager.session_scope() as session:
            time.sleep(0.2)  # Hold connection for 200ms
            session.execute(text("SELECT 1")).scalar()

    # Create more concurrent connections than base pool size
    threads = []
    for _ in range(7):  # Should cause pool overflow
        thread = threading.Thread(target=run_query)
        thread.start()
        threads.append(thread)

    # Wait a bit and check pool stats
    time.sleep(0.1)
    peak_stats = get_pool_stats()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    final_stats = get_pool_stats()

    # Verify pool scaled up and back down
    assert peak_stats["checkedout"] > initial_stats["checkedout"]
    assert final_stats["checkedout"] == initial_stats["checkedout"]

def test_connection_error_handling(db_manager):
    """Test handling of connection errors and retries."""
    with pytest.raises(Exception):
        with db_manager.session_scope() as session:
            # Force a connection error by executing invalid SQL
            session.execute(text("SELECT * FROM nonexistent_table"))

def test_long_running_transaction(db_manager):
    """Test handling of long-running transactions."""
    with db_manager.session_scope() as session:
        # Start transaction
        session.execute(text("SELECT 1"))
        
        # Simulate long-running work
        time.sleep(1)
        
        # Verify connection still valid
        result = session.execute(text("SELECT 2")).scalar()
        assert result == 2

def test_health_check_metrics(db_manager):
    """Test health check provides accurate metrics."""
    # Create some activity
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for _ in range(3):
            futures.append(executor.submit(lambda: db_manager.check_health()))
    
    # Get health metrics
    health_status = db_manager.check_health()
    
    assert health_status["status"] == "healthy"
    assert "pool" in health_status
    pool_stats = health_status["pool"]
    
    # Verify pool metrics are present and reasonable
    assert isinstance(pool_stats["size"], int)
    assert isinstance(pool_stats["checkedin"], int)
    assert isinstance(pool_stats["overflow"], int)
    assert isinstance(pool_stats["checkedout"], int)

def test_transaction_isolation(db_manager):
    """Test transaction isolation and rollback."""
    # Create a test table
    with db_manager.session_scope() as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS test_transactions (
                id SERIAL PRIMARY KEY,
                value INTEGER
            )
        """))
    
    try:
        # Test transaction rollback
        with pytest.raises(Exception):
            with db_manager.session_scope() as session:
                session.execute(text("INSERT INTO test_transactions (value) VALUES (1)"))
                raise Exception("Forced rollback")
        
        # Verify transaction was rolled back
        with db_manager.session_scope() as session:
            count = session.execute(
                text("SELECT COUNT(*) FROM test_transactions")
            ).scalar()
            assert count == 0
            
    finally:
        # Cleanup
        with db_manager.session_scope() as session:
            session.execute(text("DROP TABLE IF EXISTS test_transactions"))
