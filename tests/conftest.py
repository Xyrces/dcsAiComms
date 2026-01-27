import sys
from unittest.mock import MagicMock

# Mock requests since it is not installed in the environment
mock_requests = MagicMock()
sys.modules["requests"] = mock_requests

# Mock ollama since it is not installed
mock_ollama = MagicMock()
sys.modules["ollama"] = mock_ollama
