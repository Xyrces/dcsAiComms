import sys
import time
from unittest.mock import MagicMock

# 1. Mock external dependencies
mock_ollama = MagicMock()
# Mock the chat response structure
mock_ollama.chat.return_value = {'message': {'content': 'Roger'}}
sys.modules["ollama"] = mock_ollama

mock_requests = MagicMock()
mock_response = MagicMock()
mock_response.status_code = 200
mock_requests.get.return_value = mock_response
sys.modules["requests"] = mock_requests

# 2. Import the module to be tested
sys.path.append('.')
from src.ollama_manager import OllamaManager

def benchmark():
    manager = OllamaManager()

    # Pre-check is_running to ensure it returns True
    if not manager.is_running():
        print("Error: Manager should be running via mock")
        return

    iterations = 10000
    start_time = time.perf_counter()
    for _ in range(iterations):
        manager.chat("Test prompt")
    end_time = time.perf_counter()

    total_time = end_time - start_time
    print(f"Total time for {iterations} calls: {total_time:.4f} seconds")
    print(f"Average time per call: {total_time / iterations * 1000000:.2f} microseconds")

if __name__ == "__main__":
    benchmark()
