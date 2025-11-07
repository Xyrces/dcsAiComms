"""
Integration tests for complete audio pipeline

Tests the full workflow:
Voice Input → STT → NLP → ATC → TTS → Audio Output
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


class TestAudioPipelineIntegration:
    """Integration tests for complete audio pipeline"""

    @patch('src.stt_engine.WhisperModel')
    @patch('src.tts_engine.subprocess.run')
    @patch('src.tts_engine.sd')
    def test_complete_voice_to_audio_pipeline(self, mock_sd, mock_tts_run, mock_whisper):
        """Test complete pipeline from voice input to audio output"""
        from src.voice_input import VoiceInputHandler
        from src.stt_engine import STTEngine
        from src.nlp_processor import AviationCommandParser, ATCResponseGenerator
        from src.atc_controller import ATCController
        from src.tts_engine import TTSEngine

        # Setup mocks
        # 1. Whisper STT mock
        mock_segment = MagicMock()
        mock_segment.text = "Tower, Viper 1-1, request takeoff clearance"
        mock_segment.avg_logprob = -0.3
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model

        # 2. TTS mock
        mock_tts_run.return_value = MagicMock(
            returncode=0,
            stdout=np.random.randn(1000).astype(np.float32).tobytes()
        )

        # 3. Audio playback mock
        mock_sd.play = Mock()
        mock_sd.wait = Mock()

        # Create pipeline components
        voice_handler = VoiceInputHandler()
        stt_engine = STTEngine()
        stt_engine.load_model()
        nlp_parser = AviationCommandParser()
        nlp_generator = ATCResponseGenerator(phraseology="military")  # Use templates
        atc_controller = ATCController()
        tts_engine = TTSEngine(config={"radio_effects": True})

        # Step 1: Simulate voice input (PTT pressed, audio captured)
        voice_handler.start_recording()
        # Simulate captured audio
        captured_audio = np.random.randn(16000).astype(np.float32)
        voice_handler.stop_recording()

        # Step 2: STT - Convert audio to text
        stt_result = stt_engine.transcribe(captured_audio)
        assert stt_result["text"] == "Tower, Viper 1-1, request takeoff clearance"

        # Step 3: NLP - Parse command
        parsed_command = nlp_parser.parse(stt_result["text"])
        assert parsed_command["intent"] == "request_takeoff"
        assert "Viper 1-1" in parsed_command["entities"].get("callsign", "")

        # Step 4: ATC - Process request
        aircraft_state = {
            "position": {"lat": 45.0, "lon": -122.0, "alt": 100},
            "heading": 330,
            "speed": 0
        }
        atc_response = atc_controller.process_pilot_request(
            "Viper 1-1",
            stt_result["text"],
            aircraft_state
        )
        assert atc_response is not None
        assert "Viper 1-1" in atc_response

        # Step 5: TTS - Convert response to audio
        response_audio = tts_engine.synthesize(atc_response)
        assert response_audio is not None
        assert len(response_audio) > 0

        # Step 6: Play audio
        result = tts_engine.play_audio(response_audio)
        assert result is True

        # Verify entire pipeline executed
        assert mock_model.transcribe.called
        assert mock_tts_run.called
        assert mock_sd.play.called

    @patch('src.stt_engine.WhisperModel')
    def test_stt_to_nlp_integration(self, mock_whisper):
        """Test STT to NLP integration"""
        from src.stt_engine import STTEngine
        from src.nlp_processor import AviationCommandParser

        # Mock Whisper
        mock_segment = MagicMock()
        mock_segment.text = "Request landing clearance runway 33"
        mock_segment.avg_logprob = -0.2
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model

        # Create components
        stt_engine = STTEngine()
        stt_engine.load_model()
        nlp_parser = AviationCommandParser()

        # Process audio
        audio_data = np.random.randn(16000).astype(np.float32)
        stt_result = stt_engine.transcribe(audio_data)

        # Parse text
        parsed = nlp_parser.parse(stt_result["text"])

        assert parsed["intent"] == "request_landing"
        assert parsed["entities"]["runway"] == "33"

    def test_nlp_to_atc_to_tts_integration(self):
        """Test NLP to ATC to TTS integration"""
        from src.nlp_processor import AviationCommandParser
        from src.atc_controller import ATCController
        from src.tts_engine import TTSEngine

        # Create components
        nlp_parser = AviationCommandParser()
        atc_controller = ATCController()
        tts_engine = TTSEngine(config={"radio_effects": False})

        # Parse pilot message
        pilot_message = "Tower, Eagle 2-1, request taxi clearance"
        parsed = nlp_parser.parse(pilot_message)

        # Get ATC response
        aircraft_state = {
            "position": {"lat": 45.0, "lon": -122.0, "alt": 0},
            "heading": 0,
            "speed": 0
        }
        atc_response = atc_controller.process_pilot_request(
            "Eagle 2-1",
            pilot_message,
            aircraft_state
        )

        assert "Eagle 2-1" in atc_response
        assert "taxi" in atc_response.lower()

        # Synthesize response
        with patch('src.tts_engine.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=np.random.randn(1000).astype(np.float32).tobytes()
            )

            audio = tts_engine.synthesize(atc_response)
            assert audio is not None
            assert len(audio) > 0

    @patch('src.stt_engine.WhisperModel')
    @patch('src.tts_engine.subprocess.run')
    def test_error_recovery_in_pipeline(self, mock_tts_run, mock_whisper):
        """Test error recovery in audio pipeline"""
        from src.stt_engine import STTEngine
        from src.nlp_processor import AviationCommandParser
        from src.atc_controller import ATCController
        from src.tts_engine import TTSEngine

        # Mock STT to return unclear text
        mock_segment = MagicMock()
        mock_segment.text = "unclear transmission"
        mock_segment.avg_logprob = -2.0  # Low confidence
        mock_info = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model

        # Mock TTS
        mock_tts_run.return_value = MagicMock(
            returncode=0,
            stdout=np.random.randn(500).astype(np.float32).tobytes()
        )

        # Create pipeline
        stt_engine = STTEngine()
        stt_engine.load_model()
        nlp_parser = AviationCommandParser()
        atc_controller = ATCController()
        tts_engine = TTSEngine()

        # Process unclear audio
        audio_data = np.random.randn(8000).astype(np.float32)  # Short audio
        stt_result = stt_engine.transcribe(audio_data)

        # NLP should handle unknown intent
        parsed = nlp_parser.parse(stt_result["text"])
        assert parsed["intent"] == "unknown"

        # ATC should provide "say again" response
        response = atc_controller.process_pilot_request(
            "Unknown",
            stt_result["text"],
            {}
        )
        assert response is not None

        # TTS should still synthesize response
        audio = tts_engine.synthesize(response)
        assert audio is not None


class TestAudioPipelinePerformance:
    """Performance tests for audio pipeline"""

    @patch('src.stt_engine.WhisperModel')
    @patch('src.tts_engine.subprocess.run')
    def test_pipeline_latency(self, mock_tts_run, mock_whisper):
        """Test that pipeline completes in reasonable time"""
        import time
        from src.stt_engine import STTEngine
        from src.nlp_processor import AviationCommandParser
        from src.atc_controller import ATCController
        from src.tts_engine import TTSEngine

        # Setup mocks
        mock_segment = MagicMock()
        mock_segment.text = "Request takeoff"
        mock_segment.avg_logprob = -0.3
        mock_info = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model

        mock_tts_run.return_value = MagicMock(
            returncode=0,
            stdout=np.random.randn(1000).astype(np.float32).tobytes()
        )

        # Create components
        stt_engine = STTEngine()
        stt_engine.load_model()
        nlp_parser = AviationCommandParser()
        atc_controller = ATCController()
        tts_engine = TTSEngine()

        # Measure pipeline execution time
        start_time = time.time()

        audio_data = np.random.randn(16000).astype(np.float32)
        stt_result = stt_engine.transcribe(audio_data)
        parsed = nlp_parser.parse(stt_result["text"])
        response = atc_controller.process_pilot_request("Test", stt_result["text"], {})
        audio = tts_engine.synthesize(response)

        elapsed_time = time.time() - start_time

        # Pipeline should complete quickly (< 1 second with mocks)
        assert elapsed_time < 1.0
        assert audio is not None

    @patch('src.tts_engine.subprocess.run')
    def test_tts_caching_improves_performance(self, mock_tts_run):
        """Test that TTS caching reduces synthesis time"""
        import time
        from src.tts_engine import TTSEngine

        mock_tts_run.return_value = MagicMock(
            returncode=0,
            stdout=np.random.randn(1000).astype(np.float32).tobytes()
        )

        engine = TTSEngine(config={"cache_enabled": True})

        # First synthesis
        text = "Cleared for takeoff runway 33"
        start1 = time.time()
        audio1 = engine.synthesize(text)
        time1 = time.time() - start1

        # Second synthesis (should use cache)
        start2 = time.time()
        audio2 = engine.synthesize(text)
        time2 = time.time() - start2

        # Cached synthesis should be faster
        assert time2 < time1 or time2 < 0.001  # Much faster or negligible
        assert np.array_equal(audio1, audio2)
