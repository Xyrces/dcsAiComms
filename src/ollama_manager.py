"""
Ollama Manager - Automatic Ollama Process Management
Handles auto-launch, health checking, and model management for Ollama LLM
"""

import subprocess
import time
import requests
import concurrent.futures
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OllamaManager:
    """
    Manages Ollama process lifecycle and provides interface for chat interactions

    Features:
    - Auto-launch Ollama server if not running
    - Health check monitoring
    - Automatic model download
    - Graceful shutdown
    - Robust error handling with retries
    """

    def __init__(self, port: int = 11434, model: str = "llama3.2:3b", timeout: int = 30):
        """
        Initialize OllamaManager

        Args:
            port: Port for Ollama server (default: 11434)
            model: Model name to use (default: llama3.2:3b)
            timeout: Seconds to wait for Ollama to start (default: 30)
        """
        self.ollama_port = port
        self.model_name = model
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://localhost:{self.ollama_port}"

        # Performance optimization: Cache status to avoid blocking HTTP requests
        self._is_running_cache: bool = False
        self._last_check_time: float = 0
        self._check_interval: float = 5.0  # Seconds to cache the result
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._check_future: Optional[concurrent.futures.Future] = None

        logger.info(f"OllamaManager initialized with model={model}, port={port}")

    def _check_server_status(self) -> bool:
        """
        Perform actual HTTP check for Ollama server status.
        Updates internal cache.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            is_running = response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            is_running = False

        self._is_running_cache = is_running
        self._last_check_time = time.time()
        return is_running

    def is_running(self, force_refresh: bool = False) -> bool:
        """
        Check if Ollama server is responding.
        Uses caching to avoid blocking HTTP requests unless force_refresh is True.

        Args:
            force_refresh: If True, performs a blocking check and updates cache.

        Returns:
            True if server is known to be running, False otherwise
        """
        if force_refresh:
            return self._check_server_status()

        # Check if cache is expired
        time_since_check = time.time() - self._last_check_time
        if time_since_check > self._check_interval:
            # Check if a check is already running
            if self._check_future is None or self._check_future.done():
                self._check_future = self._executor.submit(self._check_server_status)

        return self._is_running_cache

    def start(self) -> bool:
        """
        Launch Ollama server as background process

        Returns:
            True if Ollama is running (was already running or successfully started)
            False if failed to start within timeout
        """
        # Check if already running (force check)
        if self.is_running(force_refresh=True):
            logger.info("Ollama already running")
            return True

        try:
            logger.info("Launching Ollama server...")

            # Launch ollama serve in background
            # On Windows, use CREATE_NEW_PROCESS_GROUP to allow graceful termination
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0

            self.process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags
            )

            # Wait for server to be ready (max timeout seconds)
            for i in range(self.timeout):
                time.sleep(1)
                if self.is_running(force_refresh=True):
                    logger.info(f"Ollama server started successfully after {i+1} seconds")
                    return True

            logger.error(f"Ollama server failed to start within {self.timeout} seconds")
            return False

        except FileNotFoundError:
            logger.error("Ollama not found. Please install Ollama from https://ollama.com/download")
            return False
        except Exception as e:
            logger.error(f"Error starting Ollama: {e}")
            return False

    def ensure_model(self) -> bool:
        """
        Download model if not present

        Returns:
            True if model is available or successfully downloaded
            False if download fails
        """
        try:
            import ollama

            # Check if model exists
            models_response = ollama.list()
            available_models = [m['name'] for m in models_response.get('models', [])]

            if self.model_name in available_models:
                logger.info(f"Model {self.model_name} already available")
                return True

            logger.info(f"Downloading model {self.model_name}...")
            ollama.pull(self.model_name)
            logger.info(f"Model {self.model_name} downloaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error ensuring model: {e}")
            return False

    def stop(self) -> None:
        """
        Stop Ollama server if it was started by this manager
        """
        # Shutdown executor
        self._executor.shutdown(wait=False)

        if self.process:
            try:
                logger.info("Stopping Ollama server...")
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("Ollama server stopped")
            except Exception as e:
                logger.error(f"Error stopping Ollama: {e}")
            finally:
                self.process = None

    def chat(self, prompt: str, context: Optional[dict] = None, max_retries: int = 3) -> Optional[str]:
        """
        Send a chat message to Ollama

        Args:
            prompt: The message to send
            context: Optional context dictionary for aviation-specific info
            max_retries: Number of retries on failure (default: 3)

        Returns:
            Response string from Ollama, or None if failed
        """
        if not self.is_running():
            logger.error("Cannot chat: Ollama is not running")
            return None

        for attempt in range(max_retries):
            try:
                import ollama

                # Build messages with context if provided
                messages = []
                if context:
                    system_prompt = self._build_system_prompt(context)
                    messages.append({"role": "system", "content": system_prompt})

                messages.append({"role": "user", "content": prompt})

                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    options={
                        "temperature": 0.3,  # Lower temperature for more consistent ATC responses
                        "num_predict": 100,  # Limit response length for brevity
                    }
                )

                return response['message']['content']

            except Exception as e:
                logger.warning(f"Chat attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry
                else:
                    logger.error(f"All {max_retries} chat attempts failed")
                    return None

    def _build_system_prompt(self, context: dict) -> str:
        """
        Build system prompt with aviation context

        Args:
            context: Dictionary with aviation context (callsign, position, state, etc.)

        Returns:
            Formatted system prompt
        """
        prompt_parts = ["You are an Air Traffic Controller."]

        if context.get('airbase'):
            prompt_parts.append(f"Location: {context['airbase']}")

        if context.get('callsign'):
            prompt_parts.append(f"Aircraft: {context['callsign']}")

        if context.get('aircraft_type'):
            prompt_parts.append(f"Type: {context['aircraft_type']}")

        if context.get('position'):
            prompt_parts.append(f"Position: {context['position']}")

        if context.get('state'):
            prompt_parts.append(f"Current State: {context['state']}")

        prompt_parts.append("Respond using proper US military ATC phraseology.")
        prompt_parts.append("Be concise (1-2 sentences).")

        return " ".join(prompt_parts)

    def process_atc_request(self, text: str, context: dict) -> Optional[str]:
        """
        Process an ATC request with aviation context

        Args:
            text: The pilot's transmission
            context: Aviation context dictionary

        Returns:
            ATC response or None if failed
        """
        prompt = f"Pilot transmission: \"{text}\"\n\nProvide appropriate ATC response:"
        return self.chat(prompt, context=context)

    def __enter__(self):
        """Context manager entry - start Ollama"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop Ollama"""
        self.stop()


# Fallback response generator for when Ollama is unavailable
class FallbackATCResponder:
    """
    Simple rule-based fallback for critical scenarios when Ollama is unavailable
    """

    RESPONSES = {
        'takeoff': "Cleared for takeoff",
        'land': "Cleared to land",
        'taxi': "Cleared to taxi",
        'startup': "Cleared for startup",
        'hold': "Hold position",
        'climb': "Climb and maintain",
        'descend': "Descend and maintain",
        'turn': "Turn heading",
    }

    @staticmethod
    def get_response(text: str) -> str:
        """
        Get simple rule-based response

        Args:
            text: Input text

        Returns:
            Simple ATC response
        """
        text_lower = text.lower()

        for keyword, response in FallbackATCResponder.RESPONSES.items():
            if keyword in text_lower:
                return response

        return "Roger"
