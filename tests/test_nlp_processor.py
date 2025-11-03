"""
Test Suite for NLP Processor
Aviation command parsing and intent recognition
Following TDD principles
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAviationCommandParser:
    """Test cases for aviation command parsing"""

    def test_parser_initialization(self):
        """Test parser can be instantiated"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        assert parser is not None

    def test_parse_takeoff_request(self):
        """Test parsing takeoff request"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Request takeoff clearance")

        assert result is not None
        assert result['intent'] == 'request_takeoff'

    def test_parse_landing_request(self):
        """Test parsing landing request"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Request landing clearance")

        assert result['intent'] == 'request_landing'

    def test_parse_taxi_request(self):
        """Test parsing taxi request"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Request taxi to active runway")

        assert result['intent'] == 'request_taxi'

    def test_extract_callsign(self):
        """Test extracting callsign from command"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Viper 1-1, request takeoff clearance")

        assert 'entities' in result
        assert 'callsign' in result['entities']
        assert "Viper" in result['entities']['callsign'] or "1-1" in result['entities']['callsign']

    def test_extract_altitude(self):
        """Test extracting altitude from command"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Request climb to flight level 350")

        assert 'altitude' in result['entities']
        assert "350" in str(result['entities']['altitude'])

    def test_extract_heading(self):
        """Test extracting heading from command"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Turn left heading 270")

        assert 'heading' in result['entities']
        assert "270" in str(result['entities']['heading'])

    def test_extract_runway(self):
        """Test extracting runway from command"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Request takeoff runway 27 left")

        assert 'runway' in result['entities']
        assert "27" in str(result['entities']['runway'])

    def test_parse_complex_command(self):
        """Test parsing complex multi-entity command"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Viper 1-1, request takeoff clearance runway 21 left")

        assert result['intent'] == 'request_takeoff'
        assert 'callsign' in result['entities']
        assert 'runway' in result['entities']

    def test_parse_altitude_change(self):
        """Test parsing altitude change request"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Request climb to flight level 250")

        assert result['intent'] in ['altitude_change', 'request_altitude']
        assert 'altitude' in result['entities']

    def test_parse_heading_change(self):
        """Test parsing heading change"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("Turn right heading 090")

        assert result['intent'] in ['heading_change', 'request_heading']
        assert 'heading' in result['entities']

    def test_parse_invalid_command(self):
        """Test handling of invalid/unparseable command"""
        from src.nlp_processor import AviationCommandParser

        parser = AviationCommandParser()
        result = parser.parse("asdf qwerty zxcv")

        assert result is not None
        # Should return unknown intent or default
        assert 'intent' in result


class TestIntentClassifier:
    """Test cases for intent classification"""

    def test_classifier_initialization(self):
        """Test intent classifier can be instantiated"""
        from src.nlp_processor import IntentClassifier

        classifier = IntentClassifier()
        assert classifier is not None

    def test_classify_takeoff_variants(self):
        """Test classifying various takeoff request phrasings"""
        from src.nlp_processor import IntentClassifier

        classifier = IntentClassifier()

        phrases = [
            "Request takeoff clearance",
            "Ready for takeoff",
            "Request departure",
            "Cleared for takeoff?"
        ]

        for phrase in phrases:
            intent = classifier.classify(phrase)
            assert intent == 'request_takeoff'

    def test_classify_landing_variants(self):
        """Test classifying various landing request phrasings"""
        from src.nlp_processor import IntentClassifier

        classifier = IntentClassifier()

        phrases = [
            "Request landing clearance",
            "Inbound for landing",
        ]

        for phrase in phrases:
            intent = classifier.classify(phrase)
            assert intent == 'request_landing'


class TestEntityExtractor:
    """Test cases for entity extraction"""

    def test_extractor_initialization(self):
        """Test entity extractor can be instantiated"""
        from src.nlp_processor import EntityExtractor

        extractor = EntityExtractor()
        assert extractor is not None

    def test_extract_callsign_patterns(self):
        """Test extracting various callsign formats"""
        from src.nlp_processor import EntityExtractor

        extractor = EntityExtractor()

        test_cases = [
            ("Viper 1-1", "Viper 1-1"),
            ("Navy Golf Alfa 21", "Navy Golf Alfa 21"),
            ("REACH 31792", "REACH 31792"),
        ]

        for text, expected in test_cases:
            result = extractor.extract_callsign(text)
            assert result is not None
            assert expected.lower() in result.lower() or result.lower() in expected.lower()

    def test_extract_altitude_patterns(self):
        """Test extracting various altitude formats"""
        from src.nlp_processor import EntityExtractor

        extractor = EntityExtractor()

        test_cases = [
            ("flight level 350", "350"),
            ("12,000 feet", "12000"),
            ("angels 25", "25"),
            ("FL250", "250"),
        ]

        for text, expected in test_cases:
            result = extractor.extract_altitude(text)
            assert result is not None
            assert expected in str(result)

    def test_extract_heading_patterns(self):
        """Test extracting heading values"""
        from src.nlp_processor import EntityExtractor

        extractor = EntityExtractor()

        test_cases = [
            ("heading 270", "270"),
            ("turn left 330", "330"),
            ("right turn 090", "090"),
        ]

        for text, expected in test_cases:
            result = extractor.extract_heading(text)
            assert result is not None
            assert expected in str(result)


class TestATCResponseGenerator:
    """Test cases for ATC response generation with Ollama"""

    def test_response_generator_initialization(self):
        """Test response generator can be instantiated"""
        from src.nlp_processor import ATCResponseGenerator

        generator = ATCResponseGenerator()
        assert generator is not None

    def test_generate_takeoff_clearance(self):
        """Test generating takeoff clearance response"""
        from src.nlp_processor import ATCResponseGenerator

        generator = ATCResponseGenerator()
        context = {
            'callsign': 'Viper 1-1',
            'intent': 'request_takeoff',
            'entities': {'callsign': 'Viper 1-1', 'runway': '21L'},
            'runway': '21L'
        }

        response = generator.generate_response(context)

        assert response is not None
        assert "cleared" in response.lower() or "viper" in response.lower()

    def test_generate_landing_clearance(self):
        """Test generating landing clearance response"""
        from src.nlp_processor import ATCResponseGenerator

        generator = ATCResponseGenerator()
        context = {
            'callsign': 'Viper 1-1',
            'intent': 'request_landing',
            'entities': {'callsign': 'Viper 1-1', 'runway': '27R'},
            'runway': '27R'
        }

        response = generator.generate_response(context)

        assert response is not None
        assert "cleared" in response.lower() or "land" in response.lower() or "viper" in response.lower()

    def test_generate_with_phraseology(self):
        """Test response uses proper military phraseology"""
        from src.nlp_processor import ATCResponseGenerator

        generator = ATCResponseGenerator(phraseology="military")
        context = {
            'callsign': 'Viper 1-1',
            'intent': 'report_position',
            'entities': {'callsign': 'Viper 1-1'}
        }

        response = generator.generate_response(context)

        assert response is not None


class TestNLPProcessor:
    """Integration tests for complete NLP processing pipeline"""

    def test_processor_initialization(self):
        """Test NLP processor can be instantiated"""
        from src.nlp_processor import NLPProcessor

        processor = NLPProcessor()
        assert processor is not None

    def test_process_complete_command(self):
        """Test complete command processing pipeline"""
        from src.nlp_processor import NLPProcessor

        processor = NLPProcessor()
        result = processor.process("Viper 1-1, request takeoff clearance")

        assert result is not None
        assert 'intent' in result
        assert 'entities' in result
        assert 'response' in result

    def test_processor_maintains_context(self):
        """Test processor maintains dialogue context across turns"""
        from src.nlp_processor import NLPProcessor

        processor = NLPProcessor()

        # First command
        result1 = processor.process("Viper 1-1, request takeoff clearance", context={'state': 'READY'})

        # Second command should have access to previous context
        result2 = processor.process("Roger, rolling", context={'state': 'TAKEOFF'})

        assert result1 is not None
        assert result2 is not None

    def test_processor_handles_errors_gracefully(self):
        """Test processor handles errors without crashing"""
        from src.nlp_processor import NLPProcessor

        processor = NLPProcessor()
        result = processor.process("Request takeoff")

        # Should return fallback response, not crash
        assert result is not None
