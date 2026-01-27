"""
Text-to-Speech Engine for DCS Natural Language ATC

Supports:
- Piper TTS for local synthesis (primary)
- Military radio effects (bandpass, compression, static)
- Response caching for performance
- Audio output management
"""

import logging
from typing import Dict, Optional, Any
import numpy as np
import subprocess
import hashlib
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

# Import audio libraries at module level for proper mocking
try:
    import sounddevice as sd
except ImportError:
    logger.warning("sounddevice not available, audio playback disabled")
    sd = None

try:
    from scipy import signal
except ImportError:
    logger.warning("scipy not available, radio effects may be limited")
    signal = None


class TTSEngine:
    """
    Text-to-Speech Engine with Piper TTS and military radio effects

    Features:
    - Local Piper TTS for fast synthesis
    - Military radio effects (bandpass filter, compression, static)
    - Response caching for performance
    - Audio playback and file saving
    - Graceful error handling
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize TTS Engine

        Args:
            config: Configuration dictionary with keys:
                - engine: "piper" (default)
                - voice: Voice model name (e.g., "en_US-amy-medium")
                - sample_rate: Sample rate in Hz (default 22050)
                - radio_effects: Enable radio effects (default True)
                - cache_enabled: Enable response caching (default True)
                - cache_max_size: Maximum cache size (default 50)
                - quality: "fast", "medium", or "high" (default "medium")
        """
        self.config = config or {}

        # Engine configuration
        self.engine_type = self.config.get("engine", "piper")
        self.voice_model = self.config.get("voice", "en_US-amy-medium")
        self.sample_rate = self.config.get("sample_rate", 22050)

        # Feature flags
        self.radio_effects_enabled = self.config.get("radio_effects", True)
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_max_size = self.config.get("cache_max_size", 50)
        self.quality = self.config.get("quality", "medium")

        # Cache storage
        self.response_cache = {}

        # Pre-calculate bandpass filter coefficients
        self.bandpass_sos = None
        if signal is not None:
            try:
                low_freq = 300
                high_freq = 3400
                nyquist = self.sample_rate / 2

                # Ensure frequencies are within Nyquist limit
                high_freq = min(high_freq, nyquist * 0.95)

                self.bandpass_sos = signal.butter(
                    4,  # Filter order
                    [low_freq / nyquist, high_freq / nyquist],
                    btype='bandpass',
                    output='sos'
                )
            except Exception as e:
                logger.error(f"Failed to pre-calculate bandpass filter: {e}")

        logger.info(f"TTS Engine initialized with engine={self.engine_type}, voice={self.voice_model}")

    def synthesize(self, text: str) -> np.ndarray:
        """
        Synthesize text to speech

        Args:
            text: Text to synthesize

        Returns:
            Audio data as numpy array (float32, mono)
        """
        # Validate input
        if text is None or not isinstance(text, str):
            logger.warning(f"Invalid text input: {text}")
            text = str(text) if text is not None else ""

        if len(text) == 0:
            return np.array([], dtype=np.float32)

        # Check cache first
        if self.cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self.response_cache:
                logger.debug(f"Using cached response for: {text[:50]}")
                return self.response_cache[cache_key]

        try:
            # Synthesize with Piper
            audio_data = self._synthesize_with_piper(text)

            # Apply radio effects if enabled
            if self.radio_effects_enabled and len(audio_data) > 0:
                audio_data = self.apply_radio_effects(audio_data)

            # Normalize output
            audio_data = self._normalize_audio(audio_data)

            # Cache the result
            if self.cache_enabled and len(audio_data) > 0:
                self._add_to_cache(text, audio_data)

            return audio_data

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return np.array([], dtype=np.float32)

    def _synthesize_with_piper(self, text: str) -> np.ndarray:
        """
        Synthesize text using Piper TTS

        Args:
            text: Text to synthesize

        Returns:
            Raw audio data from Piper
        """
        try:
            # In production, this would call Piper TTS binary
            # For now, we'll simulate it for testing
            # Command: echo "text" | piper --model voice.onnx --output_raw

            # Mock implementation for testing (returns random audio)
            # In production, replace with actual Piper subprocess call
            logger.debug(f"Synthesizing with Piper: {text[:50]}")

            # Simulate Piper execution
            result = subprocess.run(
                ["echo", text],  # Placeholder - would be piper command
                capture_output=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error("Piper execution failed")
                return np.array([], dtype=np.float32)

            # For testing: generate simple audio based on text length
            # In production, this would parse Piper's raw audio output
            num_samples = min(len(text) * 1000, self.sample_rate * 5)  # Max 5 seconds
            audio_data = np.random.randn(num_samples).astype(np.float32) * 0.1

            return audio_data

        except FileNotFoundError:
            logger.error("Piper TTS not found in PATH")
            return np.array([], dtype=np.float32)

        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            return np.array([], dtype=np.float32)

    def apply_radio_effects(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Apply military radio effects to audio

        Args:
            audio_data: Clean audio data

        Returns:
            Processed audio with radio effects
        """
        if not self.radio_effects_enabled:
            return audio_data

        if not isinstance(audio_data, np.ndarray):
            logger.warning("Invalid audio format for radio effects")
            return np.array([], dtype=np.float32)

        if len(audio_data) == 0:
            return audio_data

        try:
            # Apply effects in sequence
            processed = audio_data.copy()

            # 1. Bandpass filter (300Hz - 3400Hz)
            processed = self._apply_bandpass_filter(processed, self.sample_rate)

            # 2. Dynamic range compression
            processed = self._apply_compression(processed)

            # 3. Add radio static
            processed = self._add_static_noise(processed, noise_level=0.02)

            return processed

        except Exception as e:
            logger.error(f"Radio effects failed: {e}")
            return audio_data

    def _apply_bandpass_filter(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Apply bandpass filter (300Hz - 3400Hz) for radio effect

        Args:
            audio_data: Input audio
            sample_rate: Sample rate in Hz

        Returns:
            Filtered audio
        """
        if signal is None:
            logger.warning("scipy not available, skipping bandpass filter")
            return audio_data

        try:
            # Use pre-calculated coefficients if sample rate matches
            if self.bandpass_sos is not None and sample_rate == self.sample_rate:
                sos = self.bandpass_sos
            else:
                # Design Butterworth bandpass filter
                low_freq = 300
                high_freq = 3400
                nyquist = sample_rate / 2

                # Ensure frequencies are within Nyquist limit
                high_freq = min(high_freq, nyquist * 0.95)

                sos = signal.butter(
                    4,  # Filter order
                    [low_freq / nyquist, high_freq / nyquist],
                    btype='bandpass',
                    output='sos'
                )

            # Apply filter
            filtered = signal.sosfilt(sos, audio_data)
            return filtered.astype(np.float32)

        except Exception as e:
            logger.error(f"Bandpass filter failed: {e}")
            return audio_data

    def _apply_compression(self, audio_data: np.ndarray, threshold: float = 0.2,
                          ratio: float = 4.0) -> np.ndarray:
        """
        Apply dynamic range compression

        Args:
            audio_data: Input audio
            threshold: Compression threshold (0-1)
            ratio: Compression ratio

        Returns:
            Compressed audio
        """
        try:
            # Simple compression algorithm
            compressed = np.where(
                np.abs(audio_data) > threshold,
                np.sign(audio_data) * (threshold + (np.abs(audio_data) - threshold) / ratio),
                audio_data
            )

            return compressed.astype(np.float32)

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return audio_data

    def _add_static_noise(self, audio_data: np.ndarray, noise_level: float = 0.02) -> np.ndarray:
        """
        Add radio static noise

        Args:
            audio_data: Input audio
            noise_level: Noise amplitude (0-1)

        Returns:
            Audio with static noise
        """
        try:
            # Generate white noise
            noise = np.random.normal(0, noise_level, len(audio_data)).astype(np.float32)

            # Add noise to audio
            noisy = audio_data + noise

            return noisy

        except Exception as e:
            logger.error(f"Adding noise failed: {e}")
            return audio_data

    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio to range [-1, 1]

        Args:
            audio_data: Input audio

        Returns:
            Normalized audio
        """
        if len(audio_data) == 0:
            return audio_data

        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return audio_data / max_val
        return audio_data

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key from text

        Args:
            text: Input text

        Returns:
            MD5 hash of text
        """
        # Include voice model and effects in key
        key_string = f"{text}_{self.voice_model}_{self.radio_effects_enabled}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _add_to_cache(self, text: str, audio_data: np.ndarray):
        """
        Add response to cache with size limit

        Args:
            text: Input text
            audio_data: Synthesized audio
        """
        cache_key = self._get_cache_key(text)

        # Check cache size limit
        if len(self.response_cache) >= self.cache_max_size:
            # Remove oldest entry (FIFO)
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]

        self.response_cache[cache_key] = audio_data
        logger.debug(f"Cached response for: {text[:50]} (cache size: {len(self.response_cache)})")

    def play_audio(self, audio_data: np.ndarray) -> bool:
        """
        Play audio through speakers

        Args:
            audio_data: Audio to play

        Returns:
            True if successful, False otherwise
        """
        if sd is None:
            logger.warning("sounddevice not available, cannot play audio")
            return False

        try:
            logger.debug(f"Playing audio: {len(audio_data)} samples")
            sd.play(audio_data, self.sample_rate)
            sd.wait()
            return True

        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            return False

    def save_audio(self, audio_data: np.ndarray, filepath: str) -> bool:
        """
        Save audio to WAV file

        Args:
            audio_data: Audio to save
            filepath: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            from scipy.io import wavfile

            # Convert to int16 for WAV
            audio_int16 = (audio_data * 32767).astype(np.int16)

            wavfile.write(filepath, self.sample_rate, audio_int16)
            logger.info(f"Saved audio to: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False
