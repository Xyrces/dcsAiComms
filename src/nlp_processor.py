"""
NLP Processor - Aviation Command Parsing and Response Generation
Handles intent recognition, entity extraction, and ATC response generation using Ollama
"""

import re
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classifies aviation command intents using rule-based patterns
    Fast and accurate for well-defined aviation commands
    """

    # Intent patterns (keyword-based for speed)
    INTENT_PATTERNS = {
        'request_takeoff': [
            r'\b(request|ready for|cleared for)\s+(takeoff|departure)',
            r'\btakeoff clearance\b',
            r'\brequest departure\b',
        ],
        'request_landing': [
            r'\b(request|ready for|cleared for)\s+landing',
            r'\blanding clearance\b',
            r'\binbound for landing\b',
            r'\brequest to land\b',
        ],
        'request_taxi': [
            r'\b(request|ready for)\s+taxi',
            r'\btaxi clearance\b',
            r'\btaxi to\b',
        ],
        'request_startup': [
            r'\b(request|ready for)\s+startup',
            r'\bstartup clearance\b',
        ],
        'altitude_change': [
            r'\b(climb|descend|maintain)\s+(and maintain|to|altitude)',
            r'\brequest (climb|descent)\b',
            r'\bflight level\b',
        ],
        'heading_change': [
            r'\b(turn|heading)\s+(left|right|to)?\s*\d{3}',
            r'\brequest heading\b',
        ],
        'speed_change': [
            r'\b(increase|decrease|maintain)\s+speed',
            r'\b\d+\s+knots\b',
        ],
        'report_position': [
            r'\breporting\b',
            r'\bposition\b',
            r'\bmiles (north|south|east|west)\b',
        ],
        'hold_position': [
            r'\bhold (short|position)\b',
            r'\bholding\b',
        ],
        'roger': [
            r'\b(roger|copy|wilco|affirm)\b',
        ],
        'emergency': [
            r'\b(mayday|emergency|pan pan)\b',
        ],
    }

    def __init__(self):
        # Compile patterns for efficiency
        self.compiled_patterns = {
            intent: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for intent, patterns in self.INTENT_PATTERNS.items()
        }

    def classify(self, text: str) -> str:
        """
        Classify intent from text

        Args:
            text: Input command text

        Returns:
            Intent classification
        """
        text_lower = text.lower()

        # Check each intent pattern
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    logger.debug(f"Classified intent: {intent}")
                    return intent

        # Default to unknown
        logger.debug("Unknown intent")
        return 'unknown'


class EntityExtractor:
    """
    Extracts aviation-specific entities from text
    Uses regex patterns optimized for aviation terminology
    """

    # Entity extraction patterns
    PATTERNS = {
        'callsign': [
            r'\b([A-Z][a-z]+\s+\d+-\d+)\b',  # Viper 1-1
            r'\b(Navy\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+\d+)\b',  # Navy Golf Alfa 21
            r'\b([A-Z]+\s+\d{4,})\b',  # REACH 31792
            r'\b(N\d+[A-Z]{1,2})\b',  # N978CP
        ],
        'altitude': [
            r'\bflight level\s+(\d{2,3})\b',  # flight level 350
            r'\bFL\s*(\d{2,3})\b',  # FL350
            r'\b([\d,]+)\s*feet\b',  # 12,000 feet
            r'\bangels?\s+(\d+)\b',  # angels 25
        ],
        'heading': [
            r'\bheading\s+(\d{3})\b',  # heading 270
            r'\b(left|right)\s+(\d{3})\b',  # turn left 330
            r'\bturn\s+.*?(\d{3})\b',  # turn 090
        ],
        'runway': [
            r'\brunway\s+(\d{1,2}[LRC]?)\b',  # runway 27L
            r'\bRWY\s+(\d{1,2}[LRC]?)\b',  # RWY 09R
        ],
        'speed': [
            r'\b(\d{2,3})\s+knots\b',  # 250 knots
            r'\bmach\s+([\d.]+)\b',  # mach 0.82
        ],
        'frequency': [
            r'\b(\d{3}\.\d{1,3})\b',  # 118.3
            r'\bguard\b',  # Special frequency
        ],
    }

    def __init__(self):
        # Compile patterns
        self.compiled_patterns = {
            entity: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for entity, patterns in self.PATTERNS.items()
        }

    def extract_callsign(self, text: str) -> Optional[str]:
        """Extract callsign from text"""
        for pattern in self.compiled_patterns['callsign']:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    def extract_altitude(self, text: str) -> Optional[str]:
        """Extract altitude from text"""
        for pattern in self.compiled_patterns['altitude']:
            match = pattern.search(text)
            if match:
                altitude = match.group(1).replace(',', '')
                return altitude
        return None

    def extract_heading(self, text: str) -> Optional[str]:
        """Extract heading from text"""
        for pattern in self.compiled_patterns['heading']:
            match = pattern.search(text)
            if match:
                # Get the last group (the digits)
                groups = match.groups()
                return groups[-1]
        return None

    def extract_runway(self, text: str) -> Optional[str]:
        """Extract runway from text"""
        for pattern in self.compiled_patterns['runway']:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    def extract_all(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract all entities from text

        Args:
            text: Input text

        Returns:
            Dictionary of extracted entities
        """
        entities = {}

        entities['callsign'] = self.extract_callsign(text)
        entities['altitude'] = self.extract_altitude(text)
        entities['heading'] = self.extract_heading(text)
        entities['runway'] = self.extract_runway(text)

        # Filter out None values
        return {k: v for k, v in entities.items() if v is not None}


class AviationCommandParser:
    """
    Complete aviation command parser
    Combines intent classification and entity extraction
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse aviation command

        Args:
            text: Input command text

        Returns:
            Dictionary with intent and entities
        """
        intent = self.intent_classifier.classify(text)
        entities = self.entity_extractor.extract_all(text)

        result = {
            'intent': intent,
            'entities': entities,
            'raw_text': text
        }

        logger.debug(f"Parsed command: {result}")
        return result


class ATCResponseGenerator:
    """
    Generates ATC responses using Ollama or fallback templates
    """

    # Fallback response templates
    TEMPLATE_RESPONSES = {
        'request_takeoff': "{callsign}, cleared for takeoff runway {runway}",
        'request_landing': "{callsign}, cleared to land runway {runway}",
        'request_taxi': "{callsign}, taxi via {taxiway} to runway {runway}",
        'request_startup': "{callsign}, cleared for startup",
        'altitude_change': "{callsign}, climb and maintain {altitude}",
        'heading_change': "{callsign}, turn {direction} heading {heading}",
        'roger': "{callsign}, roger",
        'hold_position': "{callsign}, hold position",
        'unknown': "{callsign}, say again",
    }

    def __init__(self, phraseology: str = "military"):
        """
        Initialize response generator

        Args:
            phraseology: Style of phraseology (military or civilian)
        """
        self.phraseology = phraseology
        self.ollama_manager = None

        # Try to import and initialize Ollama
        try:
            from src.ollama_manager import OllamaManager
            self.ollama_manager = OllamaManager()
        except Exception as e:
            logger.warning(f"Could not initialize Ollama: {e}")

    def generate_response(self, context: Dict[str, Any]) -> str:
        """
        Generate ATC response

        Args:
            context: Context dictionary with intent, entities, and state

        Returns:
            ATC response string
        """
        intent = context.get('intent', 'unknown')
        entities = context.get('entities', {})
        callsign = entities.get('callsign', 'Aircraft')

        # Try Ollama first if available
        if self.ollama_manager and self.ollama_manager.is_running():
            try:
                response = self._generate_with_ollama(context)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"Ollama generation failed: {e}")

        # Fallback to template-based response
        return self._generate_from_template(intent, entities, callsign)

    def _generate_with_ollama(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Generate response using Ollama

        Args:
            context: Context dictionary

        Returns:
            Generated response or None if failed
        """
        intent = context.get('intent', 'unknown')
        entities = context.get('entities', {})
        raw_text = context.get('raw_text', '')

        # Build prompt for Ollama
        prompt = f"""You are an Air Traffic Controller using US military radio procedures.

Pilot transmission: "{raw_text}"
Intent: {intent}
Entities: {entities}

Provide a brief, authentic ATC response (1-2 sentences max).
Use proper military phraseology."""

        response = self.ollama_manager.chat(prompt, context={'phraseology': self.phraseology})
        return response

    def _generate_from_template(self, intent: str, entities: Dict, callsign: str) -> str:
        """
        Generate response from template

        Args:
            intent: Classified intent
            entities: Extracted entities
            callsign: Aircraft callsign

        Returns:
            Template-based response
        """
        template = self.TEMPLATE_RESPONSES.get(intent, self.TEMPLATE_RESPONSES['unknown'])

        # Fill in template with entities
        try:
            response = template.format(
                callsign=callsign,
                **entities
            )
        except KeyError:
            # Missing required entity, use simpler response
            response = f"{callsign}, roger"

        return response


class NLPProcessor:
    """
    Main NLP processor that orchestrates the complete pipeline
    """

    def __init__(self, phraseology: str = "military"):
        """
        Initialize NLP processor

        Args:
            phraseology: Style of phraseology (military or civilian)
        """
        self.parser = AviationCommandParser()
        self.response_generator = ATCResponseGenerator(phraseology=phraseology)
        self.context_history: List[Dict] = []

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process aviation command end-to-end

        Args:
            text: Input command text
            context: Optional additional context (state, position, etc.)

        Returns:
            Complete processing result with intent, entities, and response
        """
        try:
            # Parse command
            parsed = self.parser.parse(text)

            # Merge with additional context
            if context:
                parsed.update(context)

            # Generate response
            response = self.response_generator.generate_response(parsed)
            parsed['response'] = response

            # Store in history for context
            self.context_history.append(parsed)
            if len(self.context_history) > 10:
                self.context_history.pop(0)

            logger.info(f"Processed: {text} -> {response}")
            return parsed

        except Exception as e:
            logger.error(f"Error processing command: {e}")

            # Return fallback result
            return {
                'intent': 'unknown',
                'entities': {},
                'raw_text': text,
                'response': "Say again",
                'error': str(e)
            }

    def get_context_history(self) -> List[Dict]:
        """
        Get recent command history

        Returns:
            List of recent processed commands
        """
        return self.context_history

    def clear_history(self):
        """Clear context history"""
        self.context_history = []


# Aviation phraseology reference
PHRASEOLOGY = {
    "startup": [
        "{callsign}, cleared for startup, altimeter {altimeter}",
        "{callsign}, startup approved, advise when ready to taxi"
    ],
    "taxi": [
        "{callsign}, taxi to runway {runway} via {taxiway}",
        "{callsign}, hold short of runway {runway}",
        "{callsign}, cross runway {runway}, taxi to spot {spot}"
    ],
    "takeoff": [
        "{callsign}, wind {wind}, cleared for takeoff runway {runway}",
        "{callsign}, runway {runway}, cleared for immediate takeoff",
        "{callsign}, line up and wait runway {runway}"
    ],
    "departure": [
        "{callsign}, contact departure on {frequency}",
        "{callsign}, cleared for departure, fly runway heading",
        "{callsign}, turn left heading {heading}, climb and maintain {altitude}"
    ],
    "enroute": [
        "{callsign}, climb and maintain {altitude}",
        "{callsign}, turn {direction} heading {heading}",
        "{callsign}, reduce speed to {speed} knots",
        "{callsign}, contact {facility} on {frequency}"
    ],
    "approach": [
        "{callsign}, descend and maintain {altitude}",
        "{callsign}, turn {direction} heading {heading}, expect vectors for ILS runway {runway}",
        "{callsign}, cleared ILS runway {runway} approach"
    ],
    "landing": [
        "{callsign}, cleared to land runway {runway}, wind {wind}",
        "{callsign}, go around, I say again go around",
        "{callsign}, make short approach runway {runway}"
    ],
}
