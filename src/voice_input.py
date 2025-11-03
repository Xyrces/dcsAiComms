"""
Voice Input Handler - PTT Detection and Audio Capture

This module handles:
- Push-to-talk (PTT) key detection
- Real-time audio capture from microphone
- Audio buffer management
- Voice activity detection (VAD)
- Audio device management

Author: DCS Natural Language ATC Project
"""

import logging
import numpy as np
from typing import Optional, Dict, List, Any
import threading


logger = logging.getLogger(__name__)


# Mock imports for audio libraries (will be real in production)
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    logger.warning("sounddevice not available, using mock")
    SOUNDDEVICE_AVAILABLE = False
    # Create mock for testing
    class MockSD:
        class InputStream:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                pass
            def stop(self):
                pass
            def close(self):
                pass
        @staticmethod
        def query_devices(*args, **kwargs):
            return []
        @staticmethod
        def default_device(*args, **kwargs):
            return {}
    sd = MockSD()

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    logger.warning("keyboard not available, using mock")
    KEYBOARD_AVAILABLE = False
    # Create mock for testing
    class MockKeyboard:
        @staticmethod
        def is_pressed(key):
            return False
    keyboard = MockKeyboard()


class VoiceInputHandler:
    """
    Handles voice input with PTT detection and audio capture.

    Manages microphone input, PTT key monitoring, and audio buffering
    for speech recognition integration.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Voice Input Handler.

        Args:
            config: Configuration dictionary with keys:
                - ptt_key: PTT key combination (default: 'ctrl+shift')
                - sample_rate: Audio sample rate (default: 16000)
                - channels: Number of audio channels (default: 1)
                - chunk_size: Audio chunk size (default: 1024)
                - max_buffer_seconds: Maximum buffer duration (default: 30)
                - vad_threshold: Voice activity detection threshold (default: 0.01)
                - continuous_mode: Continuous recording without PTT (default: False)
        """
        self.config = config or {}

        # Audio configuration
        self.sample_rate = self.config.get('sample_rate', 16000)
        self.channels = self.config.get('channels', 1)
        self.chunk_size = self.config.get('chunk_size', 1024)
        self.max_buffer_seconds = self.config.get('max_buffer_seconds', 30)
        self.vad_threshold = self.config.get('vad_threshold', 0.01)

        # PTT configuration
        self.ptt_key = self.config.get('ptt_key', 'ctrl+shift')
        self.continuous_mode = self.config.get('continuous_mode', False)

        # State
        self.is_recording = False
        self._buffer = np.array([], dtype=np.float32)
        self._lock = threading.Lock()
        self._stream = None
        self.device_index = None

        logger.info(f"Voice Input Handler initialized (SR={self.sample_rate}, PTT={self.ptt_key})")

    def start_recording(self) -> bool:
        """
        Start audio recording.

        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_recording:
            logger.warning("Already recording")
            return True

        try:
            # Create audio stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                device=self.device_index
            )
            self._stream.start()
            self.is_recording = True
            logger.info("Recording started")
            return True

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            return False

    def stop_recording(self) -> bool:
        """
        Stop audio recording.

        Returns:
            bool: True if stopped successfully
        """
        if not self.is_recording:
            logger.warning("Not recording")
            return True

        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self.is_recording = False
            logger.info("Recording stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False

    def _audio_callback(self, indata, frames, time_info, status):
        """
        Audio input callback (called by sounddevice).

        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Timing information
            status: Status flags
        """
        if status:
            logger.warning(f"Audio callback status: {status}")

        try:
            if indata is None or frames == 0:
                return

            # Convert to 1D array if needed
            audio_data = indata.flatten() if indata.ndim > 1 else indata

            with self._lock:
                # Append to buffer
                self._buffer = np.concatenate([self._buffer, audio_data])

                # Limit buffer size
                max_samples = self.sample_rate * self.max_buffer_seconds
                if len(self._buffer) > max_samples:
                    # Keep only most recent data
                    self._buffer = self._buffer[-max_samples:]

        except Exception as e:
            logger.error(f"Error in audio callback: {e}")

    def get_audio_data(self) -> Optional[np.ndarray]:
        """
        Get recorded audio data.

        Returns:
            numpy array of audio samples or None
        """
        with self._lock:
            if len(self._buffer) > 0:
                return self._buffer.copy()
            return None

    def clear_buffer(self):
        """Clear audio buffer."""
        with self._lock:
            self._buffer = np.array([], dtype=np.float32)
            logger.debug("Audio buffer cleared")

    def is_ptt_pressed(self) -> bool:
        """
        Check if PTT key is pressed.

        Returns:
            bool: True if PTT key is pressed
        """
        try:
            return keyboard.is_pressed(self.ptt_key)
        except Exception as e:
            logger.error(f"Error checking PTT key: {e}")
            return False

    def check_ptt_and_record(self):
        """
        Check PTT state and start/stop recording accordingly.

        This should be called periodically in a loop.
        """
        if self.continuous_mode:
            # In continuous mode, always record
            if not self.is_recording:
                self.start_recording()
            return

        # PTT mode
        ptt_pressed = self.is_ptt_pressed()

        if ptt_pressed and not self.is_recording:
            # PTT pressed, start recording
            logger.info("PTT pressed, starting recording")
            self.clear_buffer()  # Clear old data
            self.start_recording()

        elif not ptt_pressed and self.is_recording:
            # PTT released, stop recording
            logger.info("PTT released, stopping recording")
            self.stop_recording()

    def detect_voice_activity(self, audio: np.ndarray) -> bool:
        """
        Detect if audio contains voice activity.

        Simple energy-based VAD using RMS amplitude.

        Args:
            audio: Audio data array

        Returns:
            bool: True if voice activity detected
        """
        if audio is None or len(audio) == 0:
            return False

        # Calculate RMS amplitude
        rms = np.sqrt(np.mean(audio**2))

        # Compare against threshold
        return rms > self.vad_threshold

    # Audio device management

    def list_input_devices(self) -> List[Dict]:
        """
        List available audio input devices.

        Returns:
            List of device dictionaries
        """
        try:
            devices = sd.query_devices()
            if not isinstance(devices, list):
                devices = [devices]

            # Filter for input devices
            input_devices = [
                d for d in devices
                if isinstance(d, dict) and d.get('max_input_channels', 0) > 0
            ]
            return input_devices

        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []

    def get_default_input_device(self) -> Optional[Dict]:
        """
        Get default audio input device.

        Returns:
            Device dictionary or None
        """
        try:
            device = sd.query_devices(kind='input')
            return device if isinstance(device, dict) else None

        except Exception as e:
            logger.error(f"Error getting default device: {e}")
            return None

    def set_input_device(self, device_index: int):
        """
        Set the audio input device.

        Args:
            device_index: Index of the device to use
        """
        self.device_index = device_index
        logger.info(f"Input device set to index {device_index}")

        # If currently recording, restart with new device
        if self.is_recording:
            self.stop_recording()
            self.start_recording()

    def shutdown(self):
        """Clean shutdown of voice input handler."""
        logger.info("Shutting down voice input handler")

        if self.is_recording:
            self.stop_recording()

        self.clear_buffer()


if __name__ == '__main__':
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create handler
    handler = VoiceInputHandler(config={
        'ptt_key': 'ctrl+shift',
        'sample_rate': 16000,
        'continuous_mode': False
    })

    print("Voice Input Handler Test")
    print("=" * 50)

    # List devices
    print("\nAvailable input devices:")
    devices = handler.list_input_devices()
    for i, device in enumerate(devices):
        print(f"  {i}: {device.get('name', 'Unknown')}")

    # Get default device
    default = handler.get_default_input_device()
    if default:
        print(f"\nDefault device: {default.get('name', 'Unknown')}")

    print("\nPress Ctrl+Shift to record, release to stop")
    print("Press Ctrl+C to exit\n")

    try:
        import time
        while True:
            # Check PTT
            handler.check_ptt_and_record()

            # If we have audio, check for voice activity
            if not handler.is_recording and len(handler._buffer) > 0:
                audio = handler.get_audio_data()
                has_voice = handler.detect_voice_activity(audio)
                print(f"Audio captured: {len(audio)} samples, Voice: {has_voice}")
                handler.clear_buffer()

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nShutting down...")
        handler.shutdown()
