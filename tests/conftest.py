import pytest
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

@pytest.fixture(autouse=True)
def load_env():
    """Load environment variables for all tests"""
    load_dotenv()
    
    # Verify required environment variables for login tests
    required_vars = ["OPENAI_API_KEY", "X_USERNAME", "X_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.fail(f"Missing required environment variables: {', '.join(missing_vars)}")

# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    ) 