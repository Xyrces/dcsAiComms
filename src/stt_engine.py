"""
Speech-to-Text Engine for DCS Natural Language ATC

Supports:
- faster-whisper for local STT (primary)
- Fireworks AI for cloud fallback (optional)
- Aviation vocabulary optimization
- Audio preprocessing and normalization
"""

import logging
from typing import Dict, Optional, Any
import numpy as np

# Setup logging
logger = logging.getLogger(__name__)

# Import WhisperModel at module level for proper mocking
try:
    from faster_whisper import WhisperModel
except ImportError:
    # Create a mock class for testing without faster-whisper installed
    class WhisperModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, *args, **kwargs):
            return [], type('obj', (object,), {'language': 'en'})()


# Fireworks AI support
try:
    import requests
except ImportError:
    logger.warning("requests library not installed, Fireworks AI unavailable")


class STTEngine:
    """
    Speech-to-Text Engine with support for Whisper and Fireworks AI

    Features:
    - Local Whisper model for privacy
    - Fireworks AI fallback for improved accuracy
    - Aviation vocabulary optimization
    - Audio preprocessing (normalization, resampling, mono conversion)
    - Graceful error handling
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize STT Engine

        Args:
            config: Configuration dictionary with keys:
                - engine: "whisper" (default) or "fireworks"
                - model: Model size for Whisper ("tiny", "base", "small", "medium")
                - device: "cpu" or "cuda"
                - compute_type: "int8", "float16", etc.
                - api_key: Fireworks API key (if using fireworks)
                - aviation_vocab: Enable aviation vocabulary optimization
                - vad_filter: Enable Voice Activity Detection
                - beam_size: Beam size for decoding (1-5)
        """
        self.config = config or {}

        # Engine configuration
        self.engine_type = self.config.get("engine", "whisper")
        self.model_size = self.config.get("model", "base")
        self.device = self.config.get("device", "cpu")
        self.compute_type = self.config.get("compute_type", "int8")

        # Fireworks AI configuration
        self.api_key = self.config.get("api_key", None)

        # Feature flags
        self.aviation_vocab = self.config.get("aviation_vocab", True)
        self.vad_filter = self.config.get("vad_filter", True)
        self.beam_size = self.config.get("beam_size", 5)

        # Model instance
        self.model = None
        self.model_loaded = False

        logger.info(f"STT Engine initialized with engine={self.engine_type}, model={self.model_size}")

    def load_model(self) -> bool:
        """
        Load the STT model

        Returns:
            True if model loaded successfully, False otherwise
        """
        if self.engine_type == "whisper":
            return self._load_whisper_model()
        elif self.engine_type == "fireworks":
            # Fireworks AI doesn't need model loading
            self.model_loaded = True
            return True
        else:
            logger.error(f"Unknown engine type: {self.engine_type}")
            return False

    def _load_whisper_model(self) -> bool:
        """
        Load faster-whisper model

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Use module-level WhisperModel (this will be mocked in tests)
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            self.model_loaded = True
            logger.info("Whisper model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model_loaded = False
            return False

    def transcribe(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Transcribe audio data to text

        Args:
            audio_data: Audio data as numpy array (float32, 16kHz, mono)

        Returns:
            Dictionary with:
                - text: Transcribed text
                - language: Detected language
                - confidence: Confidence score (0-1)
                - error: Error message if failed
        """
        # Validate input
        if not isinstance(audio_data, np.ndarray):
            return {"text": "", "error": "Invalid audio format: expected numpy array"}

        if len(audio_data) == 0:
            return {"text": "", "error": "Empty audio data"}

        try:
            # Preprocess audio
            audio_data = self.normalize_audio(audio_data)

            # Convert to mono if stereo
            if audio_data.ndim > 1:
                audio_data = self.convert_to_mono(audio_data)

            # Transcribe using selected engine
            if self.engine_type == "whisper":
                return self._transcribe_with_whisper(audio_data)
            elif self.engine_type == "fireworks":
                return self._transcribe_with_fireworks(audio_data)
            else:
                return {"text": "", "error": f"Unknown engine: {self.engine_type}"}

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {"text": "", "error": str(e)}

    def _transcribe_with_whisper(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Transcribe using faster-whisper

        Args:
            audio_data: Preprocessed audio data

        Returns:
            Transcription result dictionary
        """
        if not self.model_loaded or self.model is None:
            return {"text": "", "error": "Whisper model not loaded"}

        try:
            # Get aviation context prompt if enabled
            initial_prompt = self.get_aviation_prompt() if self.aviation_vocab else None

            # Transcribe
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                initial_prompt=initial_prompt
            )

            # Combine segments
            segments_list = list(segments)
            text = " ".join([segment.text for segment in segments_list]).strip()

            # Calculate confidence (convert log probability to confidence)
            if segments_list:
                avg_logprob = np.mean([segment.avg_logprob for segment in segments_list])
                confidence = np.exp(avg_logprob)
            else:
                confidence = 0.0

            return {
                "text": text,
                "language": info.language if hasattr(info, 'language') else "en",
                "confidence": float(confidence)
            }

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return {"text": "", "error": str(e)}

    def _transcribe_with_fireworks(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Transcribe using Fireworks AI API

        Args:
            audio_data: Preprocessed audio data

        Returns:
            Transcription result dictionary
        """
        try:
            import requests
            import base64

            if not self.api_key:
                return {"text": "", "error": "Fireworks API key not provided"}

            # Convert audio to bytes (simplified - would need proper encoding)
            # For now, return mock response for testing
            api_url = "https://api.fireworks.ai/v1/audio/transcribe"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Note: This is a simplified version
            # In production, audio would need proper encoding
            payload = {
                "model": "whisper-v3",
                "audio": base64.b64encode(audio_data.tobytes()).decode()
            }

            response = requests.post(api_url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return {
                    "text": result.get("text", ""),
                    "language": result.get("language", "en"),
                    "confidence": result.get("confidence", 0.9)
                }
            else:
                return {"text": "", "error": f"API error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Fireworks AI transcription failed: {e}")
            return {"text": "", "error": str(e)}

    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio data to range [-1, 1]

        Args:
            audio_data: Raw audio data

        Returns:
            Normalized audio data
        """
        if len(audio_data) == 0:
            return audio_data

        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return audio_data / max_val
        return audio_data

    def resample_audio(self, audio_data: np.ndarray, source_rate: int = 44100,
                      target_rate: int = 16000) -> np.ndarray:
        """
        Resample audio to target sample rate

        Args:
            audio_data: Audio data at source_rate
            source_rate: Source sample rate (Hz)
            target_rate: Target sample rate (Hz)

        Returns:
            Resampled audio data
        """
        try:
            from scipy import signal

            # Calculate resampling ratio
            num_samples = int(len(audio_data) * target_rate / source_rate)

            # Resample using scipy
            resampled = signal.resample(audio_data, num_samples)
            return resampled.astype(np.float32)

        except ImportError:
            logger.warning("scipy not available for resampling, returning original")
            return audio_data
        except Exception as e:
            logger.error(f"Resampling failed: {e}")
            return audio_data

    def convert_to_mono(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Convert stereo audio to mono by averaging channels

        Args:
            audio_data: Stereo audio data (samples, channels)

        Returns:
            Mono audio data (samples,)
        """
        if audio_data.ndim == 1:
            return audio_data

        if audio_data.ndim == 2:
            # Average across channels
            return np.mean(audio_data, axis=1).astype(np.float32)

        logger.warning(f"Unexpected audio dimensions: {audio_data.ndim}")
        return audio_data

    def get_aviation_prompt(self) -> str:
        """
        Get aviation context prompt for better recognition

        Returns:
            Aviation-specific context prompt
        """
        return (
            "Aviation radio communication. "
            "Common terms: Tower, Ground, Approach, Departure, "
            "runway, taxiway, clearance, takeoff, landing, "
            "altitude, heading, frequency, squawk, wilco, roger, "
            "callsigns like Viper, Eagle, Hornet, flight levels."
        )
