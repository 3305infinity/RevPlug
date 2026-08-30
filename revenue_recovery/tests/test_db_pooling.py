import pytest
from app.db.session import PostgresConnection, init_pool, close_pool, get_pool

@pytest.fixture(autouse=True)
def manage_pool():
    # Only test the interface logic by using an invalid DSN that will fail on real connect
    # Since we can't easily connect to a real DB without mocking or knowing the URL is valid,
    # we just mock get_pool() behavior in tests or test the pool initialization
    init_pool()
    yield
    close_pool()

def test_pool_singleton():
    pool1 = get_pool()
    pool2 = get_pool()
    assert pool1 is pool2

def test_postgres_connection_interface(monkeypatch):
    """Test that PostgresConnection proxies to the pool correctly."""
    class MockCursor:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.query = None
            self.params = None
            
        def execute(self, query, params=None):
            self.query = query
            self.params = params
            
        def fetchone(self):
            return {"id": 1, "value": "test"}
            
        def fetchall(self):
            return [{"id": 1, "value": "test"}]
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockConnection:
        def __init__(self):
            self.committed = False
            self.rollbacked = False
            self.cursor_called = False
            
        def cursor(self, **kwargs):
            self.cursor_called = True
            return MockCursor(**kwargs)
            
        def commit(self):
            self.committed = True
            
        def rollback(self):
            self.rollbacked = True
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockPool:
        def connection(self):
            return MockConnection()

    monkeypatch.setattr("app.db.session.get_pool", lambda: MockPool())
    
    conn = PostgresConnection()
    
    # Test execute
    conn.execute("SELECT 1")
    
    # Test fetchone
    row = conn.fetchone("SELECT 1")
    assert row == {"id": 1, "value": "test"}
    
    # Test fetchall
    rows = conn.fetchall("SELECT 1")
    assert rows == [{"id": 1, "value": "test"}]
