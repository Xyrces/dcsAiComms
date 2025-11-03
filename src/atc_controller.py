"""
ATC Logic Engine - State Machine and Flight Phase Management

This module handles the core ATC logic, including:
- Flight phase state machine (cold start -> airborne -> landing)
- ATC response generation based on current phase
- Queue management for multiple aircraft
- Integration with NLP processor for intent understanding

Author: DCS Natural Language ATC Project
"""

import logging
from enum import Enum
from typing import Dict, Optional, Any, List
from collections import deque, defaultdict
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class FlightPhase(Enum):
    """
    Flight phases for state machine tracking.

    Represents the complete lifecycle of an aircraft from cold start to shutdown.
    """
    COLD_START = 'cold_start'
    STARTUP = 'startup'
    TAXI = 'taxi'
    TAKEOFF = 'takeoff'
    AIRBORNE = 'airborne'
    APPROACH = 'approach'
    LANDING = 'landing'
    LANDED = 'landed'


@dataclass
class QueueEntry:
    """Entry in an ATC queue"""
    callsign: str
    priority: bool = False


class ATCController:
    """
    Main ATC Logic Engine.

    Manages flight phases, generates appropriate ATC responses,
    and handles queue management for multiple aircraft.
    """

    def __init__(self, nlp_processor=None):
        """
        Initialize ATC Controller.

        Args:
            nlp_processor: Optional NLPProcessor instance for command parsing
        """
        self.nlp_processor = nlp_processor
        self.aircraft_phases: Dict[str, FlightPhase] = {}
        self.queues: Dict[str, deque] = defaultdict(deque)  # Queue type -> deque of entries
        self.context: Dict[str, Dict] = {}  # Aircraft context/history

        logger.info("ATC Controller initialized")

    def get_aircraft_phase(self, callsign: str) -> FlightPhase:
        """
        Get the current flight phase for an aircraft.

        Args:
            callsign: Aircraft callsign

        Returns:
            Current FlightPhase (default: COLD_START)
        """
        return self.aircraft_phases.get(callsign, FlightPhase.COLD_START)

    def set_aircraft_phase(self, callsign: str, phase: FlightPhase):
        """
        Set the flight phase for an aircraft.

        Args:
            callsign: Aircraft callsign
            phase: FlightPhase to set
        """
        old_phase = self.aircraft_phases.get(callsign)
        self.aircraft_phases[callsign] = phase

        if old_phase != phase:
            logger.info(f"{callsign} phase changed: {old_phase} -> {phase}")

    def get_all_aircraft_phases(self) -> Dict[str, FlightPhase]:
        """
        Get all aircraft phases.

        Returns:
            Dictionary mapping callsigns to FlightPhases
        """
        return self.aircraft_phases.copy()

    def update_aircraft_phase_from_state(self, callsign: str, state: Dict[str, Any]):
        """
        Automatically update aircraft phase based on aircraft state.

        Uses altitude, speed, and other telemetry to determine appropriate phase.

        Args:
            callsign: Aircraft callsign
            state: Aircraft state dictionary (from DCS Bridge)
        """
        current_phase = self.get_aircraft_phase(callsign)

        speed = state.get('speed', 0)
        position = state.get('position', {})
        altitude = position.get('alt', 0) if position else 0

        # Simple heuristics for phase detection
        # Airborne: high altitude and speed
        if altitude > 500 and speed > 100:
            # Check if approaching (descending at low altitude)
            if altitude < 3000 and current_phase == FlightPhase.AIRBORNE:
                self.set_aircraft_phase(callsign, FlightPhase.APPROACH)
            elif current_phase not in [FlightPhase.AIRBORNE, FlightPhase.APPROACH]:
                self.set_aircraft_phase(callsign, FlightPhase.AIRBORNE)

        # On ground
        elif altitude < 200 and speed < 50:
            if current_phase in [FlightPhase.APPROACH, FlightPhase.LANDING]:
                self.set_aircraft_phase(callsign, FlightPhase.LANDED)

    def process_pilot_request(
        self,
        callsign: str,
        message: str,
        aircraft_state: Dict[str, Any]
    ) -> str:
        """
        Process a pilot's radio request and generate ATC response.

        Args:
            callsign: Aircraft callsign
            message: Pilot's message text
            aircraft_state: Current aircraft state

        Returns:
            ATC response string
        """
        current_phase = self.get_aircraft_phase(callsign)

        # Parse message with NLP processor if available
        if self.nlp_processor:
            try:
                from src.nlp_processor import ATCCommandParser, ATCResponseGenerator

                parser = ATCCommandParser()
                parsed = parser.parse_command(message)

                intent = parsed.get('intent', 'unknown')
                entities = parsed.get('entities', {})

                # Generate response
                return self.generate_atc_response(
                    callsign=callsign,
                    intent=intent,
                    entities=entities,
                    context={'phase': current_phase.value, 'state': aircraft_state}
                )
            except Exception as e:
                logger.error(f"Error processing request with NLP: {e}")

        # Fallback: simple pattern matching
        message_lower = message.lower()

        if 'startup' in message_lower:
            self.set_aircraft_phase(callsign, FlightPhase.STARTUP)
            return f"{callsign}, cleared for startup, altimeter 2992"

        elif 'taxi' in message_lower:
            self.set_aircraft_phase(callsign, FlightPhase.TAXI)
            return f"{callsign}, taxi to runway 31, hold short"

        elif 'takeoff' in message_lower:
            if current_phase in [FlightPhase.TAXI, FlightPhase.TAKEOFF]:
                self.set_aircraft_phase(callsign, FlightPhase.TAKEOFF)
                return f"{callsign}, wind 270 at 10, cleared for takeoff runway 31"
            else:
                return f"{callsign}, unable, taxi to runway first"

        elif 'landing' in message_lower or 'land' in message_lower:
            if current_phase in [FlightPhase.APPROACH, FlightPhase.AIRBORNE]:
                self.set_aircraft_phase(callsign, FlightPhase.LANDING)
                return f"{callsign}, cleared to land runway 31, wind 270 at 10"
            else:
                return f"{callsign}, unable, not in position for landing"

        else:
            return f"{callsign}, roger"

    def generate_atc_response(
        self,
        callsign: str,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate ATC response based on intent and context.

        Args:
            callsign: Aircraft callsign
            intent: Classified intent from NLP
            entities: Extracted entities (runway, altitude, etc.)
            context: Context including flight phase

        Returns:
            ATC response string
        """
        phase = context.get('phase', 'cold_start')
        runway = entities.get('runway', '31')
        altitude = entities.get('altitude')
        heading = entities.get('heading')

        # Response templates based on intent
        if intent == 'request_startup':
            self.set_aircraft_phase(callsign, FlightPhase.STARTUP)
            return f"{callsign}, cleared for startup, altimeter 2992"

        elif intent == 'request_taxi':
            self.set_aircraft_phase(callsign, FlightPhase.TAXI)
            return f"{callsign}, taxi to runway {runway} via taxiway alpha, hold short"

        elif intent == 'request_takeoff':
            if phase in ['taxi', 'takeoff']:
                self.set_aircraft_phase(callsign, FlightPhase.TAKEOFF)
                return f"{callsign}, wind 270 at 10, cleared for takeoff runway {runway}"
            else:
                return f"{callsign}, unable, not in position for takeoff"

        elif intent == 'request_altitude_change':
            if altitude:
                return f"{callsign}, climb and maintain {altitude}"
            else:
                return f"{callsign}, say altitude"

        elif intent == 'request_heading_change':
            if heading:
                return f"{callsign}, turn heading {heading}"
            else:
                return f"{callsign}, say heading"

        elif intent == 'request_landing':
            if phase in ['approach', 'airborne']:
                self.set_aircraft_phase(callsign, FlightPhase.LANDING)
                return f"{callsign}, cleared to land runway {runway}, wind 270 at 10"
            else:
                return f"{callsign}, unable, not in position for landing"

        else:
            return f"{callsign}, roger"

    # Queue Management Methods

    def add_to_queue(self, callsign: str, queue_type: str, priority: bool = False):
        """
        Add aircraft to a queue (takeoff, landing, etc.).

        Args:
            callsign: Aircraft callsign
            queue_type: Type of queue (takeoff, landing, etc.)
            priority: Whether this is a priority request (emergency, etc.)
        """
        entry = QueueEntry(callsign=callsign, priority=priority)

        if priority:
            # Priority entries go to front
            self.queues[queue_type].appendleft(entry)
        else:
            # Normal entries go to back
            self.queues[queue_type].append(entry)

        logger.info(f"Added {callsign} to {queue_type} queue (priority={priority})")

    def remove_from_queue(self, callsign: str, queue_type: str):
        """
        Remove aircraft from a queue.

        Args:
            callsign: Aircraft callsign
            queue_type: Type of queue
        """
        queue = self.queues[queue_type]
        self.queues[queue_type] = deque(
            [entry for entry in queue if entry.callsign != callsign]
        )
        logger.info(f"Removed {callsign} from {queue_type} queue")

    def is_in_queue(self, callsign: str, queue_type: str) -> bool:
        """
        Check if aircraft is in a queue.

        Args:
            callsign: Aircraft callsign
            queue_type: Type of queue

        Returns:
            True if in queue, False otherwise
        """
        queue = self.queues[queue_type]
        return any(entry.callsign == callsign for entry in queue)

    def get_queue_position(self, callsign: str, queue_type: str) -> Optional[int]:
        """
        Get aircraft's position in queue (0-indexed).

        Args:
            callsign: Aircraft callsign
            queue_type: Type of queue

        Returns:
            Position in queue or None if not in queue
        """
        queue = self.queues[queue_type]
        for i, entry in enumerate(queue):
            if entry.callsign == callsign:
                return i
        return None

    def get_next_in_queue(self, queue_type: str) -> Optional[str]:
        """
        Get the next aircraft in queue.

        Args:
            queue_type: Type of queue

        Returns:
            Callsign of next aircraft or None if queue empty
        """
        queue = self.queues[queue_type]
        if queue:
            return queue[0].callsign
        return None

    def clear_queue(self, queue_type: str):
        """
        Clear all entries from a queue.

        Args:
            queue_type: Type of queue to clear
        """
        count = len(self.queues[queue_type])
        self.queues[queue_type].clear()
        logger.info(f"Cleared {queue_type} queue ({count} aircraft)")


if __name__ == '__main__':
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create controller
    controller = ATCController()

    # Simulate aircraft lifecycle
    print("=== Simulating Aircraft Lifecycle ===\n")

    # Startup
    response = controller.process_pilot_request(
        "Viper 1-1",
        "Ground, Viper 1-1, request startup",
        {"speed": 0, "position": {"alt": 50}}
    )
    print(f"Pilot: Ground, Viper 1-1, request startup")
    print(f"ATC: {response}\n")

    # Taxi
    response = controller.process_pilot_request(
        "Viper 1-1",
        "Ground, Viper 1-1, request taxi",
        {"speed": 0, "position": {"alt": 50}}
    )
    print(f"Pilot: Ground, Viper 1-1, request taxi")
    print(f"ATC: {response}\n")

    # Takeoff
    response = controller.process_pilot_request(
        "Viper 1-1",
        "Tower, Viper 1-1, request takeoff clearance",
        {"speed": 0, "position": {"alt": 50}}
    )
    print(f"Pilot: Tower, Viper 1-1, request takeoff clearance")
    print(f"ATC: {response}\n")

    # Airborne
    controller.update_aircraft_phase_from_state("Viper 1-1", {
        "speed": 300,
        "position": {"alt": 5000}
    })
    print(f"Phase after takeoff: {controller.get_aircraft_phase('Viper 1-1')}\n")

    # Landing
    controller.update_aircraft_phase_from_state("Viper 1-1", {
        "speed": 200,
        "position": {"alt": 1500}
    })
    response = controller.process_pilot_request(
        "Viper 1-1",
        "Tower, Viper 1-1, request landing clearance",
        {"speed": 200, "position": {"alt": 1500}}
    )
    print(f"Pilot: Tower, Viper 1-1, request landing clearance")
    print(f"ATC: {response}\n")
