import pytest
import os
from dotenv import load_dotenv

def pytest_configure(config):
    """Configure test environment"""
    load_dotenv()
    
    # Mark integration tests
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )

@pytest.fixture(autouse=True)
def check_env_vars():
    """Ensure required environment variables are set"""
    required_vars = ["X_USERNAME", "X_PASSWORD", "OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"Missing required environment variables: {', '.join(missing)}") 