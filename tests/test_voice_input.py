"""
Tests for Voice Input Handler (PTT detection and audio capture)

Following TDD methodology - write tests first, then implement.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
import sys
from collections import deque

# Mock audio libraries before importing
sys.modules['sounddevice'] = MagicMock()
sys.modules['keyboard'] = MagicMock()


class TestVoiceInputHandler:
    """Test suite for Voice Input Handler initialization and configuration"""

    def test_handler_initialization(self):
        """Test that Voice Input Handler can be initialized"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        assert handler is not None
        assert handler.is_recording is False

    def test_handler_with_custom_config(self):
        """Test initialization with custom configuration"""
        from src.voice_input import VoiceInputHandler

        config = {
            'ptt_key': 'ctrl+shift',
            'sample_rate': 16000,
            'channels': 1
        }
        handler = VoiceInputHandler(config=config)

        assert handler.sample_rate == 16000
        assert handler.channels == 1

    def test_handler_default_config(self):
        """Test default configuration values"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()

        assert handler.sample_rate == 16000  # Standard for speech
        assert handler.channels == 1  # Mono for speech
        assert handler.chunk_size > 0

    @patch('sounddevice.InputStream')
    def test_start_recording(self, mock_stream):
        """Test starting audio recording"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.start_recording()

        assert handler.is_recording is True
        mock_stream.assert_called()

    @patch('sounddevice.InputStream')
    def test_stop_recording(self, mock_stream):
        """Test stopping audio recording"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.start_recording()
        handler.stop_recording()

        assert handler.is_recording is False

    @patch('sounddevice.InputStream')
    def test_get_audio_data(self, mock_stream):
        """Test retrieving recorded audio data"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.start_recording()

        # Simulate some audio data
        test_audio = np.zeros(1000, dtype=np.float32)
        handler._buffer = deque([test_audio])
        handler._buffer_sample_count = 1000

        audio_data = handler.get_audio_data()

        assert audio_data is not None
        assert len(audio_data) > 0

    @patch('sounddevice.InputStream')
    def test_clear_buffer(self, mock_stream):
        """Test clearing audio buffer"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler._buffer = deque([np.zeros(1000, dtype=np.float32)])
        handler._buffer_sample_count = 1000

        handler.clear_buffer()

        assert len(handler._buffer) == 0 or handler._buffer is None
        assert handler._buffer_sample_count == 0


class TestPTTDetection:
    """Test suite for Push-to-Talk detection"""

    @patch('keyboard.is_pressed')
    def test_ptt_key_detection(self, mock_is_pressed):
        """Test PTT key press detection"""
        from src.voice_input import VoiceInputHandler

        mock_is_pressed.return_value = True
        handler = VoiceInputHandler(config={'ptt_key': 'ctrl+shift'})

        is_pressed = handler.is_ptt_pressed()

        assert is_pressed is True

    @patch('keyboard.is_pressed')
    def test_ptt_key_not_pressed(self, mock_is_pressed):
        """Test PTT key not pressed"""
        from src.voice_input import VoiceInputHandler

        mock_is_pressed.return_value = False
        handler = VoiceInputHandler(config={'ptt_key': 'ctrl+shift'})

        is_pressed = handler.is_ptt_pressed()

        assert is_pressed is False

    @patch('keyboard.is_pressed')
    @patch('sounddevice.InputStream')
    def test_ptt_triggers_recording(self, mock_stream, mock_is_pressed):
        """Test that pressing PTT starts recording"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler(config={'ptt_key': 'ctrl+shift'})

        # Simulate PTT press
        mock_is_pressed.return_value = True
        handler.check_ptt_and_record()

        assert handler.is_recording is True

    @patch('keyboard.is_pressed')
    @patch('sounddevice.InputStream')
    def test_ptt_release_stops_recording(self, mock_stream, mock_is_pressed):
        """Test that releasing PTT stops recording"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler(config={'ptt_key': 'ctrl+shift'})

        # Start recording
        mock_is_pressed.return_value = True
        handler.check_ptt_and_record()

        # Release PTT
        mock_is_pressed.return_value = False
        handler.check_ptt_and_record()

        assert handler.is_recording is False


class TestAudioCapture:
    """Test suite for audio capture functionality"""

    @patch('sounddevice.InputStream')
    def test_audio_callback(self, mock_stream):
        """Test audio input callback function"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.start_recording()

        # Simulate audio callback
        indata = np.random.random((1024, 1)).astype(np.float32)
        frames = 1024
        time_info = {}
        status = None

        handler._audio_callback(indata, frames, time_info, status)

        # Buffer should contain data
        assert handler._buffer is not None

    @patch('sounddevice.InputStream')
    def test_buffer_management(self, mock_stream):
        """Test that buffer is managed correctly"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.start_recording()

        # Add audio data multiple times
        for _ in range(5):
            indata = np.random.random((1024, 1)).astype(np.float32)
            handler._audio_callback(indata, 1024, {}, None)

        # Buffer should accumulate data
        audio_data = handler.get_audio_data()
        assert len(audio_data) >= 1024 * 5

    @patch('sounddevice.InputStream')
    def test_buffer_overflow_protection(self, mock_stream):
        """Test that buffer doesn't grow unbounded"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler(config={'max_buffer_seconds': 10})
        handler.start_recording()

        # Try to add excessive audio data
        max_samples = handler.sample_rate * 10  # 10 seconds
        for _ in range(100):
            indata = np.random.random((1024, 1)).astype(np.float32)
            handler._audio_callback(indata, 1024, {}, None)

        audio_data = handler.get_audio_data()
        # Buffer should be limited
        assert len(audio_data) <= max_samples * 1.1  # Allow 10% overhead


class TestAudioDeviceManagement:
    """Test suite for audio device selection and management"""

    @patch('sounddevice.query_devices')
    def test_list_input_devices(self, mock_query):
        """Test listing available input devices"""
        from src.voice_input import VoiceInputHandler

        mock_query.return_value = [
            {'name': 'Microphone 1', 'max_input_channels': 2},
            {'name': 'Microphone 2', 'max_input_channels': 1}
        ]

        handler = VoiceInputHandler()
        devices = handler.list_input_devices()

        assert len(devices) == 2
        assert devices[0]['name'] == 'Microphone 1'

    @patch('sounddevice.query_devices')
    def test_get_default_input_device(self, mock_query):
        """Test getting default input device"""
        from src.voice_input import VoiceInputHandler

        mock_query.return_value = {'name': 'Default Mic', 'index': 0}

        handler = VoiceInputHandler()
        device = handler.get_default_input_device()

        assert device is not None
        assert device['name'] == 'Default Mic'

    @patch('sounddevice.InputStream')
    def test_set_input_device(self, mock_stream):
        """Test setting specific input device"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.set_input_device(1)

        assert handler.device_index == 1

    @patch('sounddevice.InputStream')
    def test_device_error_handling(self, mock_stream):
        """Test handling of invalid device"""
        from src.voice_input import VoiceInputHandler

        mock_stream.side_effect = Exception("Device not found")

        handler = VoiceInputHandler()
        result = handler.start_recording()

        # Should handle error gracefully
        assert result is False or handler.is_recording is False


class TestVoiceActivityDetection:
    """Test suite for voice activity detection (VAD)"""

    def test_detect_voice_activity_silence(self):
        """Test VAD with silence"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()

        # Create silent audio
        audio = np.zeros(1000, dtype=np.float32)

        has_voice = handler.detect_voice_activity(audio)

        assert has_voice == False  # Use == for numpy boolean compatibility

    def test_detect_voice_activity_speech(self):
        """Test VAD with speech-like audio"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()

        # Create audio with signal
        audio = np.random.random(1000).astype(np.float32) * 0.5

        has_voice = handler.detect_voice_activity(audio)

        assert has_voice == True  # Use == for numpy boolean compatibility

    def test_vad_threshold_configuration(self):
        """Test configurable VAD threshold"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler(config={'vad_threshold': 0.01})

        # Very quiet audio
        audio = np.random.random(1000).astype(np.float32) * 0.001

        has_voice = handler.detect_voice_activity(audio)

        # Should detect with low threshold
        assert has_voice == False  # Still below threshold, use == for numpy boolean


class TestVoiceInputIntegration:
    """Test suite for Voice Input Handler integration"""

    @patch('sounddevice.InputStream')
    @patch('keyboard.is_pressed')
    def test_complete_ptt_workflow(self, mock_is_pressed, mock_stream):
        """Test complete PTT workflow from press to audio capture"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler(config={'ptt_key': 'ctrl+shift'})

        # 1. Press PTT
        mock_is_pressed.return_value = True
        handler.check_ptt_and_record()
        assert handler.is_recording is True

        # 2. Simulate audio input
        audio_data = np.random.random((1024, 1)).astype(np.float32)
        handler._audio_callback(audio_data, 1024, {}, None)

        # 3. Release PTT
        mock_is_pressed.return_value = False
        handler.check_ptt_and_record()
        assert handler.is_recording is False

        # 4. Get recorded audio
        recorded = handler.get_audio_data()
        assert recorded is not None
        assert len(recorded) > 0

    @patch('sounddevice.InputStream')
    def test_continuous_monitoring_mode(self, mock_stream):
        """Test continuous monitoring without PTT"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler(config={'continuous_mode': True})
        handler.start_recording()

        # Should be recording without PTT
        assert handler.is_recording is True

        # Should capture audio
        audio_data = np.random.random((1024, 1)).astype(np.float32)
        handler._audio_callback(audio_data, 1024, {}, None)

        recorded = handler.get_audio_data()
        assert len(recorded) > 0

    @patch('sounddevice.InputStream')
    def test_callback_error_handling(self, mock_stream):
        """Test error handling in audio callback"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.start_recording()

        # Test with invalid data
        try:
            handler._audio_callback(None, 0, {}, None)
            # Should not crash
            assert True
        except Exception as e:
            pytest.fail(f"Audio callback should handle errors: {e}")

    @patch('sounddevice.InputStream')
    def test_shutdown_cleanup(self, mock_stream):
        """Test proper cleanup on shutdown"""
        from src.voice_input import VoiceInputHandler

        handler = VoiceInputHandler()
        handler.start_recording()

        # Add some data
        audio_data = np.random.random((1024, 1)).astype(np.float32)
        handler._audio_callback(audio_data, 1024, {}, None)

        # Shutdown
        handler.shutdown()

        # Should clean up
        assert handler.is_recording is False
        # Stream should be closed (mock would be called)
