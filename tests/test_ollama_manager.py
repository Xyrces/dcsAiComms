"""
Test Suite for OllamaManager
Following TDD principles - tests written before implementation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import time


class TestOllamaManager:
    """Test cases for OllamaManager class"""

    def test_ollama_manager_initialization(self):
        """Test OllamaManager can be instantiated with default config"""
        from src.ollama_manager import OllamaManager

        manager = OllamaManager()
        assert manager is not None
        assert manager.ollama_port == 11434
        assert manager.model_name == "llama3.2:3b"
        assert manager.process is None

    def test_ollama_manager_custom_config(self):
        """Test OllamaManager accepts custom configuration"""
        from src.ollama_manager import OllamaManager

        manager = OllamaManager(port=11435, model="llama3.1:8b")
        assert manager.ollama_port == 11435
        assert manager.model_name == "llama3.1:8b"

    @patch('requests.get')
    def test_is_running_returns_true_when_ollama_responds(self, mock_get):
        """Test is_running() returns True when Ollama server is responsive"""
        from src.ollama_manager import OllamaManager

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        manager = OllamaManager()
        assert manager.is_running() is True
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=2)

    @patch('requests.get')
    def test_is_running_returns_false_when_ollama_not_responding(self, mock_get):
        """Test is_running() returns False when Ollama server is not responsive"""
        from src.ollama_manager import OllamaManager

        mock_get.side_effect = Exception("Connection refused")

        manager = OllamaManager()
        assert manager.is_running() is False

    @patch('requests.get')
    def test_is_running_returns_false_on_non_200_status(self, mock_get):
        """Test is_running() returns False when Ollama returns non-200 status"""
        from src.ollama_manager import OllamaManager

        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        manager = OllamaManager()
        assert manager.is_running() is False

    @patch('subprocess.Popen')
    @patch('src.ollama_manager.OllamaManager.is_running')
    def test_start_ollama_when_already_running(self, mock_is_running, mock_popen):
        """Test start() returns True immediately if Ollama is already running"""
        from src.ollama_manager import OllamaManager

        mock_is_running.return_value = True

        manager = OllamaManager()
        result = manager.start()

        assert result is True
        mock_popen.assert_not_called()

    @patch('subprocess.Popen')
    @patch('src.ollama_manager.OllamaManager.is_running')
    @patch('time.sleep')
    def test_start_ollama_launches_process(self, mock_sleep, mock_is_running, mock_popen):
        """Test start() launches Ollama process and waits for it to be ready"""
        from src.ollama_manager import OllamaManager

        # First call returns False (not running), subsequent calls return True (started)
        mock_is_running.side_effect = [False, False, True]
        mock_process = Mock()
        mock_popen.return_value = mock_process

        manager = OllamaManager()
        result = manager.start()

        assert result is True
        assert manager.process == mock_process
        mock_popen.assert_called_once()
        assert mock_sleep.call_count == 2

    @patch('subprocess.Popen')
    @patch('src.ollama_manager.OllamaManager.is_running')
    @patch('time.sleep')
    def test_start_ollama_timeout(self, mock_sleep, mock_is_running, mock_popen):
        """Test start() returns False if Ollama doesn't start within timeout"""
        from src.ollama_manager import OllamaManager

        # Always returns False (never starts)
        mock_is_running.return_value = False
        mock_process = Mock()
        mock_popen.return_value = mock_process

        manager = OllamaManager(timeout=3)  # Short timeout for test
        result = manager.start()

        assert result is False
        assert mock_sleep.call_count == 3

    @patch('subprocess.Popen')
    @patch('src.ollama_manager.OllamaManager.is_running')
    def test_start_ollama_file_not_found(self, mock_is_running, mock_popen):
        """Test start() handles FileNotFoundError when Ollama is not installed"""
        from src.ollama_manager import OllamaManager

        mock_is_running.return_value = False
        mock_popen.side_effect = FileNotFoundError("ollama not found")

        manager = OllamaManager()
        result = manager.start()

        assert result is False

    @patch('ollama.list')
    def test_ensure_model_when_model_exists(self, mock_list):
        """Test ensure_model() returns True when model is already downloaded"""
        from src.ollama_manager import OllamaManager

        mock_list.return_value = {
            'models': [
                {'name': 'llama3.2:3b'},
                {'name': 'llama3.1:8b'}
            ]
        }

        manager = OllamaManager()
        result = manager.ensure_model()

        assert result is True

    @patch('ollama.pull')
    @patch('ollama.list')
    def test_ensure_model_downloads_when_missing(self, mock_list, mock_pull):
        """Test ensure_model() downloads model when not present"""
        from src.ollama_manager import OllamaManager

        mock_list.return_value = {
            'models': [
                {'name': 'llama3.1:8b'}
            ]
        }

        manager = OllamaManager()
        result = manager.ensure_model()

        assert result is True
        mock_pull.assert_called_once_with('llama3.2:3b')

    @patch('ollama.list')
    def test_ensure_model_handles_exception(self, mock_list):
        """Test ensure_model() handles exceptions gracefully"""
        from src.ollama_manager import OllamaManager

        mock_list.side_effect = Exception("Connection error")

        manager = OllamaManager()
        result = manager.ensure_model()

        assert result is False

    def test_stop_ollama_when_process_exists(self):
        """Test stop() terminates the Ollama process if it was started by manager"""
        from src.ollama_manager import OllamaManager

        manager = OllamaManager()
        mock_process = Mock()
        manager.process = mock_process

        manager.stop()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    def test_stop_ollama_when_no_process(self):
        """Test stop() handles case when no process was started"""
        from src.ollama_manager import OllamaManager

        manager = OllamaManager()
        manager.stop()  # Should not raise exception

    @patch('ollama.chat')
    @patch('src.ollama_manager.OllamaManager.is_running')
    def test_chat_with_ollama(self, mock_is_running, mock_chat):
        """Test chat() method sends messages to Ollama"""
        from src.ollama_manager import OllamaManager

        mock_is_running.return_value = True
        mock_chat.return_value = {
            'message': {'content': 'Viper 1-1, cleared for takeoff'}
        }

        manager = OllamaManager()
        result = manager.chat("Request takeoff clearance")

        assert result == 'Viper 1-1, cleared for takeoff'
        mock_chat.assert_called_once()

    @patch('src.ollama_manager.OllamaManager.is_running')
    def test_chat_fails_when_ollama_not_running(self, mock_is_running):
        """Test chat() returns None when Ollama is not running"""
        from src.ollama_manager import OllamaManager

        mock_is_running.return_value = False

        manager = OllamaManager()
        result = manager.chat("Request takeoff clearance")

        assert result is None

    @patch('ollama.chat')
    @patch('src.ollama_manager.OllamaManager.is_running')
    def test_chat_handles_exception(self, mock_is_running, mock_chat):
        """Test chat() handles exceptions during communication"""
        from src.ollama_manager import OllamaManager

        mock_is_running.return_value = True
        mock_chat.side_effect = Exception("API error")

        manager = OllamaManager()
        result = manager.chat("Request takeoff clearance")

        assert result is None
