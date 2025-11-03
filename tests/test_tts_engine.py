"""
Test suite for Text-to-Speech Engine

Tests cover:
1. TTS engine initialization with different configurations
2. Piper TTS integration and synthesis
3. Military radio effects (bandpass, compression, static)
4. Response caching for performance
5. Audio output management
6. Error handling and graceful degradation
7. Mock-friendly design for CI/CD
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import hashlib


class TestTTSEngineInitialization:
    """Test TTS engine initialization and configuration"""

    def test_engine_initialization_default_config(self):
        """Test TTS engine initializes with default configuration"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        assert engine is not None
        assert engine.engine_type == "piper"  # Default
        assert engine.voice_model is not None
        assert engine.radio_effects_enabled is True  # Default

    def test_engine_initialization_custom_config(self):
        """Test TTS engine with custom configuration"""
        from src.tts_engine import TTSEngine

        config = {
            "engine": "piper",
            "voice": "en_US-amy-medium",
            "sample_rate": 22050,
            "radio_effects": False,
            "cache_enabled": True
        }

        engine = TTSEngine(config=config)

        assert engine.engine_type == "piper"
        assert engine.voice_model == "en_US-amy-medium"
        assert engine.sample_rate == 22050
        assert engine.radio_effects_enabled is False
        assert engine.cache_enabled is True

    def test_engine_initialization_with_caching(self):
        """Test TTS engine with response caching enabled"""
        from src.tts_engine import TTSEngine

        config = {"cache_enabled": True, "cache_max_size": 100}

        engine = TTSEngine(config=config)

        assert engine.cache_enabled is True
        assert engine.cache_max_size == 100
        assert engine.response_cache == {}


class TestPiperIntegration:
    """Test Piper TTS integration"""

    @patch('src.tts_engine.subprocess.run')
    def test_synthesize_text_with_piper(self, mock_run):
        """Test text synthesis with Piper TTS"""
        from src.tts_engine import TTSEngine

        # Mock Piper output (raw audio bytes)
        mock_audio_bytes = np.random.randn(22050).astype(np.float32).tobytes()
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_audio_bytes
        )

        engine = TTSEngine()
        audio_data = engine.synthesize("Tower, Viper 1-1, cleared for takeoff")

        assert audio_data is not None
        assert isinstance(audio_data, np.ndarray)
        assert len(audio_data) > 0

    @patch('src.tts_engine.subprocess.run')
    def test_synthesize_empty_text(self, mock_run):
        """Test synthesis with empty text"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()
        audio_data = engine.synthesize("")

        assert audio_data is not None
        assert len(audio_data) == 0 or len(audio_data) < 100

    @patch('src.tts_engine.subprocess.run')
    def test_piper_failure_handling(self, mock_run):
        """Test handling of Piper TTS failure"""
        from src.tts_engine import TTSEngine

        mock_run.side_effect = Exception("Piper not found")

        engine = TTSEngine()
        audio_data = engine.synthesize("Test text")

        # Should return empty or fallback audio
        assert audio_data is not None


class TestRadioEffects:
    """Test military radio effects processing"""

    def test_apply_radio_effects(self):
        """Test applying radio effects to audio"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine(config={"radio_effects": True})

        # Create clean audio
        clean_audio = np.sin(2 * np.pi * 440 * np.arange(0, 1, 1/22050)).astype(np.float32)

        # Apply radio effects
        processed = engine.apply_radio_effects(clean_audio)

        assert processed is not None
        assert len(processed) == len(clean_audio)
        assert isinstance(processed, np.ndarray)
        # Audio should be different after effects
        assert not np.array_equal(clean_audio, processed)

    def test_bandpass_filter(self):
        """Test bandpass filter (300Hz - 3400Hz)"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        # Create audio with multiple frequencies
        sample_rate = 22050
        t = np.arange(0, 1, 1/sample_rate)
        # Mix of low (100Hz), mid (1000Hz), and high (5000Hz) frequencies
        audio = (
            np.sin(2 * np.pi * 100 * t) +
            np.sin(2 * np.pi * 1000 * t) +
            np.sin(2 * np.pi * 5000 * t)
        ).astype(np.float32)

        filtered = engine._apply_bandpass_filter(audio, sample_rate)

        assert filtered is not None
        assert len(filtered) == len(audio)
        # The filtered audio should be different (frequencies outside 300-3400Hz reduced)
        assert not np.array_equal(audio, filtered)

    def test_compression(self):
        """Test dynamic range compression"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        # Create audio with high dynamic range
        audio = np.concatenate([
            np.full(1000, 0.1),   # Quiet
            np.full(1000, 0.9)    # Loud
        ]).astype(np.float32)

        compressed = engine._apply_compression(audio)

        assert compressed is not None
        assert len(compressed) == len(audio)
        # Dynamic range should be reduced
        original_range = np.max(audio) - np.min(audio)
        compressed_range = np.max(compressed) - np.min(compressed)
        # Compressed range should be smaller or similar
        assert compressed_range <= original_range * 1.1

    def test_add_static_noise(self):
        """Test adding radio static noise"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        # Create clean audio
        audio = np.zeros(1000, dtype=np.float32)

        noisy = engine._add_static_noise(audio, noise_level=0.05)

        assert noisy is not None
        assert len(noisy) == len(audio)
        # Audio should have noise added
        assert not np.array_equal(audio, noisy)
        assert np.std(noisy) > 0  # Should have some variation

    def test_radio_effects_disabled(self):
        """Test that radio effects can be disabled"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine(config={"radio_effects": False})

        audio = np.random.randn(1000).astype(np.float32)
        processed = engine.apply_radio_effects(audio)

        # Should return original audio when effects disabled
        assert np.array_equal(audio, processed)


class TestResponseCaching:
    """Test response caching for performance"""

    @patch('src.tts_engine.subprocess.run')
    def test_cache_stores_responses(self, mock_run):
        """Test that synthesized responses are cached"""
        from src.tts_engine import TTSEngine

        mock_audio_bytes = np.random.randn(1000).astype(np.float32).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_audio_bytes)

        engine = TTSEngine(config={"cache_enabled": True})

        text = "Tower, cleared for takeoff"
        audio1 = engine.synthesize(text)
        audio2 = engine.synthesize(text)

        # Should use cache for second call
        assert mock_run.call_count == 1  # Only called once
        assert np.array_equal(audio1, audio2)

    @patch('src.tts_engine.subprocess.run')
    def test_cache_key_generation(self, mock_run):
        """Test cache key generation from text"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        text = "Test message"
        key = engine._get_cache_key(text)

        assert isinstance(key, str)
        assert len(key) > 0
        # Same text should produce same key
        assert key == engine._get_cache_key(text)

    @patch('src.tts_engine.subprocess.run')
    def test_cache_max_size_limit(self, mock_run):
        """Test cache size limit enforcement"""
        from src.tts_engine import TTSEngine

        mock_audio_bytes = np.random.randn(100).astype(np.float32).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_audio_bytes)

        engine = TTSEngine(config={"cache_enabled": True, "cache_max_size": 5})

        # Generate more responses than cache size
        for i in range(10):
            engine.synthesize(f"Message {i}")

        # Cache should not exceed max size
        assert len(engine.response_cache) <= 5

    def test_cache_disabled(self):
        """Test that caching can be disabled"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine(config={"cache_enabled": False})

        assert engine.cache_enabled is False


class TestAudioOutput:
    """Test audio output management"""

    @patch('src.tts_engine.sd')
    def test_play_audio(self, mock_sd):
        """Test playing audio through speakers"""
        from src.tts_engine import TTSEngine

        mock_sd.play = Mock()
        mock_sd.wait = Mock()

        engine = TTSEngine()
        audio_data = np.random.randn(1000).astype(np.float32)

        result = engine.play_audio(audio_data)

        assert result is True
        mock_sd.play.assert_called_once()
        mock_sd.wait.assert_called_once()

    @patch('src.tts_engine.sd')
    def test_play_audio_failure(self, mock_sd):
        """Test audio playback failure handling"""
        from src.tts_engine import TTSEngine

        mock_sd.play = Mock(side_effect=Exception("Audio device not found"))

        engine = TTSEngine()
        audio_data = np.random.randn(1000).astype(np.float32)

        result = engine.play_audio(audio_data)

        assert result is False

    def test_save_audio_to_file(self):
        """Test saving audio to WAV file"""
        from src.tts_engine import TTSEngine
        import tempfile

        engine = TTSEngine()
        audio_data = np.random.randn(1000).astype(np.float32)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            result = engine.save_audio(audio_data, tmp.name)

        assert result is True


class TestErrorHandling:
    """Test error handling and graceful degradation"""

    def test_synthesize_with_invalid_text(self):
        """Test synthesis with invalid text input"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        # Test with None
        audio = engine.synthesize(None)
        assert audio is not None

        # Test with non-string
        audio = engine.synthesize(12345)
        assert audio is not None

    @patch('src.tts_engine.subprocess.run')
    def test_piper_not_available(self, mock_run):
        """Test graceful handling when Piper is not available"""
        from src.tts_engine import TTSEngine

        mock_run.side_effect = FileNotFoundError("piper not found")

        engine = TTSEngine()
        audio = engine.synthesize("Test")

        # Should return silent or empty audio
        assert audio is not None

    def test_invalid_audio_format(self):
        """Test handling of invalid audio format"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        # Test with invalid data type
        result = engine.apply_radio_effects("not an array")

        assert result is not None


class TestTTSEngineIntegration:
    """Integration tests for complete TTS workflow"""

    @patch('src.tts_engine.subprocess.run')
    @patch('src.tts_engine.sd')
    def test_complete_tts_workflow(self, mock_sd, mock_run):
        """Test complete workflow from text to audio output"""
        from src.tts_engine import TTSEngine

        # Mock Piper synthesis
        mock_audio_bytes = np.random.randn(22050).astype(np.float32).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_audio_bytes)

        # Mock sounddevice
        mock_sd.play = Mock()
        mock_sd.wait = Mock()

        # Create engine with all features
        engine = TTSEngine(config={
            "engine": "piper",
            "voice": "en_US-amy-medium",
            "radio_effects": True,
            "cache_enabled": True
        })

        # Synthesize text
        text = "Tower, Viper 1-1, cleared for takeoff runway 33"
        audio_data = engine.synthesize(text)

        assert audio_data is not None
        assert len(audio_data) > 0

        # Play audio
        result = engine.play_audio(audio_data)
        assert result is True

        # Verify synthesis was called
        assert mock_run.called
        assert mock_sd.play.called

    @patch('src.tts_engine.subprocess.run')
    def test_cached_response_has_effects(self, mock_run):
        """Test that cached responses still have radio effects"""
        from src.tts_engine import TTSEngine

        mock_audio_bytes = np.random.randn(1000).astype(np.float32).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_audio_bytes)

        engine = TTSEngine(config={
            "radio_effects": True,
            "cache_enabled": True
        })

        text = "Test message"
        audio1 = engine.synthesize(text)
        audio2 = engine.synthesize(text)  # From cache

        # Both should be identical (effects applied before caching)
        assert np.array_equal(audio1, audio2)


class TestPerformanceOptimizations:
    """Test performance optimizations"""

    @patch('src.tts_engine.subprocess.run')
    def test_fast_synthesis_mode(self, mock_run):
        """Test fast synthesis mode for reduced latency"""
        from src.tts_engine import TTSEngine

        mock_audio_bytes = np.random.randn(1000).astype(np.float32).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_audio_bytes)

        engine = TTSEngine(config={"quality": "fast"})

        audio = engine.synthesize("Quick test")

        assert audio is not None
        # Fast mode should still work

    def test_normalize_output_audio(self):
        """Test output audio normalization"""
        from src.tts_engine import TTSEngine

        engine = TTSEngine()

        # Create audio with varying amplitudes
        audio = np.array([0.1, -0.5, 0.9, -0.2], dtype=np.float32)
        normalized = engine._normalize_audio(audio)

        assert normalized is not None
        # Should be normalized to [-1, 1] range
        assert np.max(np.abs(normalized)) <= 1.0


class TestVoiceConfiguration:
    """Test voice model configuration"""

    def test_different_voice_models(self):
        """Test initialization with different voice models"""
        from src.tts_engine import TTSEngine

        voices = ["en_US-amy-medium", "en_US-ryan-high", "en_US-lessac-medium"]

        for voice in voices:
            engine = TTSEngine(config={"voice": voice})
            assert engine.voice_model == voice

    def test_sample_rate_configuration(self):
        """Test different sample rates"""
        from src.tts_engine import TTSEngine

        rates = [16000, 22050, 44100]

        for rate in rates:
            engine = TTSEngine(config={"sample_rate": rate})
            assert engine.sample_rate == rate
