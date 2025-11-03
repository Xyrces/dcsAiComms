"""
Tests for ATC Logic Engine (State machine and flight phase management)

Following TDD methodology - write tests first, then implement.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from enum import Enum


class TestFlightPhaseEnum:
    """Test suite for FlightPhase enumeration"""

    def test_flight_phase_enum_exists(self):
        """Test that FlightPhase enum is defined"""
        from src.atc_controller import FlightPhase

        assert hasattr(FlightPhase, 'COLD_START')
        assert hasattr(FlightPhase, 'STARTUP')
        assert hasattr(FlightPhase, 'TAXI')
        assert hasattr(FlightPhase, 'TAKEOFF')
        assert hasattr(FlightPhase, 'AIRBORNE')
        assert hasattr(FlightPhase, 'APPROACH')
        assert hasattr(FlightPhase, 'LANDING')
        assert hasattr(FlightPhase, 'LANDED')

    def test_flight_phase_values(self):
        """Test that FlightPhase has correct values"""
        from src.atc_controller import FlightPhase

        assert FlightPhase.COLD_START.value == 'cold_start'
        assert FlightPhase.AIRBORNE.value == 'airborne'
        assert FlightPhase.LANDING.value == 'landing'


class TestATCController:
    """Test suite for ATC Controller logic engine"""

    def test_controller_initialization(self):
        """Test that ATC Controller can be initialized"""
        from src.atc_controller import ATCController

        controller = ATCController()
        assert controller is not None
        assert controller.aircraft_phases == {}

    def test_controller_with_nlp_processor(self):
        """Test controller initialization with NLP processor"""
        from src.atc_controller import ATCController
        from src.nlp_processor import NLPProcessor

        nlp = NLPProcessor()
        controller = ATCController(nlp_processor=nlp)

        assert controller.nlp_processor is not None

    def test_get_aircraft_phase(self):
        """Test getting current flight phase for aircraft"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.aircraft_phases["Viper 1-1"] = FlightPhase.TAXI

        phase = controller.get_aircraft_phase("Viper 1-1")
        assert phase == FlightPhase.TAXI

    def test_get_aircraft_phase_default(self):
        """Test getting flight phase for new aircraft returns COLD_START"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        phase = controller.get_aircraft_phase("Viper 1-1")
        assert phase == FlightPhase.COLD_START

    def test_set_aircraft_phase(self):
        """Test setting flight phase for aircraft"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.AIRBORNE)

        assert controller.aircraft_phases["Viper 1-1"] == FlightPhase.AIRBORNE

    def test_process_pilot_request_takeoff(self):
        """Test processing takeoff request"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.TAXI)

        response = controller.process_pilot_request(
            "Viper 1-1",
            "Tower, Viper 1-1, request takeoff clearance",
            {"speed": 0, "position": {"alt": 50}}
        )

        assert response is not None
        assert "cleared for takeoff" in response.lower() or "takeoff" in response.lower()

    def test_process_pilot_request_landing(self):
        """Test processing landing request"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.APPROACH)

        response = controller.process_pilot_request(
            "Viper 1-1",
            "Tower, Viper 1-1, request landing clearance",
            {"speed": 200, "position": {"alt": 1500}}
        )

        assert response is not None
        assert "cleared to land" in response.lower() or "landing" in response.lower()

    def test_automatic_phase_detection_airborne(self):
        """Test automatic phase detection based on aircraft state"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()

        # Aircraft on ground
        controller.update_aircraft_phase_from_state("Viper 1-1", {
            "speed": 0,
            "position": {"alt": 50}
        })
        phase = controller.get_aircraft_phase("Viper 1-1")
        assert phase in [FlightPhase.COLD_START, FlightPhase.LANDED]

        # Aircraft airborne
        controller.update_aircraft_phase_from_state("Viper 1-1", {
            "speed": 300,
            "position": {"alt": 5000}
        })
        phase = controller.get_aircraft_phase("Viper 1-1")
        assert phase == FlightPhase.AIRBORNE

    def test_automatic_phase_detection_approach(self):
        """Test automatic detection of approach phase"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.AIRBORNE)

        # Aircraft descending at low altitude
        controller.update_aircraft_phase_from_state("Viper 1-1", {
            "speed": 200,
            "position": {"alt": 1500}
        })

        phase = controller.get_aircraft_phase("Viper 1-1")
        assert phase == FlightPhase.APPROACH

    def test_process_startup_request(self):
        """Test processing startup request"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()

        response = controller.process_pilot_request(
            "Viper 1-1",
            "Ground, Viper 1-1, request startup",
            {"speed": 0, "position": {"alt": 50}}
        )

        assert response is not None
        assert "startup" in response.lower() or "altimeter" in response.lower()

    def test_process_taxi_request(self):
        """Test processing taxi request"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.STARTUP)

        response = controller.process_pilot_request(
            "Viper 1-1",
            "Ground, Viper 1-1, request taxi",
            {"speed": 0, "position": {"alt": 50}}
        )

        assert response is not None
        assert "taxi" in response.lower() or "runway" in response.lower()

    def test_invalid_phase_transition(self):
        """Test that invalid phase transitions are handled"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.COLD_START)

        # Try to request landing from cold start (invalid)
        response = controller.process_pilot_request(
            "Viper 1-1",
            "Tower, request landing",
            {"speed": 0, "position": {"alt": 50}}
        )

        # Should still return a response (negative or guidance)
        assert response is not None

    def test_get_all_aircraft_phases(self):
        """Test getting all aircraft phases"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.AIRBORNE)
        controller.set_aircraft_phase("Viper 1-2", FlightPhase.TAXI)

        phases = controller.get_all_aircraft_phases()

        assert len(phases) == 2
        assert phases["Viper 1-1"] == FlightPhase.AIRBORNE
        assert phases["Viper 1-2"] == FlightPhase.TAXI


class TestATCResponseGeneration:
    """Test suite for ATC response generation based on flight phase"""

    def test_generate_startup_clearance(self):
        """Test generating startup clearance"""
        from src.atc_controller import ATCController

        controller = ATCController()

        response = controller.generate_atc_response(
            callsign="Viper 1-1",
            intent="request_startup",
            entities={"callsign": "Viper 1-1"},
            context={"phase": "cold_start"}
        )

        assert response is not None
        assert "viper 1-1" in response.lower()

    def test_generate_taxi_clearance(self):
        """Test generating taxi clearance"""
        from src.atc_controller import ATCController

        controller = ATCController()

        response = controller.generate_atc_response(
            callsign="Viper 1-1",
            intent="request_taxi",
            entities={"callsign": "Viper 1-1", "runway": "31"},
            context={"phase": "startup"}
        )

        assert response is not None
        assert "taxi" in response.lower()

    def test_generate_takeoff_clearance(self):
        """Test generating takeoff clearance"""
        from src.atc_controller import ATCController

        controller = ATCController()

        response = controller.generate_atc_response(
            callsign="Viper 1-1",
            intent="request_takeoff",
            entities={"callsign": "Viper 1-1", "runway": "31"},
            context={"phase": "taxi"}
        )

        assert response is not None
        assert "cleared for takeoff" in response.lower() or "takeoff" in response.lower()

    def test_generate_altitude_clearance(self):
        """Test generating altitude change clearance"""
        from src.atc_controller import ATCController

        controller = ATCController()

        response = controller.generate_atc_response(
            callsign="Viper 1-1",
            intent="request_altitude_change",
            entities={"callsign": "Viper 1-1", "altitude": "10000"},
            context={"phase": "airborne"}
        )

        assert response is not None
        assert "10000" in response or "climb" in response.lower() or "maintain" in response.lower()

    def test_generate_heading_clearance(self):
        """Test generating heading change clearance"""
        from src.atc_controller import ATCController

        controller = ATCController()

        response = controller.generate_atc_response(
            callsign="Viper 1-1",
            intent="request_heading_change",
            entities={"callsign": "Viper 1-1", "heading": "270"},
            context={"phase": "airborne"}
        )

        assert response is not None
        assert "270" in response or "heading" in response.lower()

    def test_generate_landing_clearance(self):
        """Test generating landing clearance"""
        from src.atc_controller import ATCController

        controller = ATCController()

        response = controller.generate_atc_response(
            callsign="Viper 1-1",
            intent="request_landing",
            entities={"callsign": "Viper 1-1", "runway": "31"},
            context={"phase": "approach"}
        )

        assert response is not None
        assert "cleared to land" in response.lower() or "landing" in response.lower()


class TestATCQueue:
    """Test suite for ATC queue management (multiple aircraft)"""

    def test_add_aircraft_to_queue(self):
        """Test adding aircraft to ATC queue"""
        from src.atc_controller import ATCController

        controller = ATCController()

        controller.add_to_queue("Viper 1-1", "takeoff")
        assert controller.is_in_queue("Viper 1-1", "takeoff")

    def test_remove_aircraft_from_queue(self):
        """Test removing aircraft from queue"""
        from src.atc_controller import ATCController

        controller = ATCController()

        controller.add_to_queue("Viper 1-1", "takeoff")
        controller.remove_from_queue("Viper 1-1", "takeoff")

        assert not controller.is_in_queue("Viper 1-1", "takeoff")

    def test_get_queue_position(self):
        """Test getting position in queue"""
        from src.atc_controller import ATCController

        controller = ATCController()

        controller.add_to_queue("Viper 1-1", "takeoff")
        controller.add_to_queue("Viper 1-2", "takeoff")
        controller.add_to_queue("Viper 1-3", "takeoff")

        position = controller.get_queue_position("Viper 1-2", "takeoff")
        assert position == 1  # 0-indexed

    def test_handle_queue_priority(self):
        """Test queue respects priority (emergency, etc.)"""
        from src.atc_controller import ATCController

        controller = ATCController()

        controller.add_to_queue("Viper 1-1", "landing")
        controller.add_to_queue("Viper 1-2", "landing", priority=True)

        # Priority aircraft should be first
        next_aircraft = controller.get_next_in_queue("landing")
        assert next_aircraft == "Viper 1-2"

    def test_clear_queue(self):
        """Test clearing queue"""
        from src.atc_controller import ATCController

        controller = ATCController()

        controller.add_to_queue("Viper 1-1", "takeoff")
        controller.add_to_queue("Viper 1-2", "takeoff")

        controller.clear_queue("takeoff")

        assert not controller.is_in_queue("Viper 1-1", "takeoff")
        assert not controller.is_in_queue("Viper 1-2", "takeoff")


class TestATCIntegration:
    """Test suite for ATC Controller integration with NLP and DCS Bridge"""

    def test_integration_with_nlp_processor(self):
        """Test ATC controller integrates with NLP processor"""
        from src.atc_controller import ATCController
        from src.nlp_processor import NLPProcessor

        nlp = NLPProcessor()
        controller = ATCController(nlp_processor=nlp)

        # Process a complete request
        response = controller.process_pilot_request(
            "Viper 1-1",
            "Tower, Viper 1-1, request takeoff clearance",
            {"speed": 0, "position": {"alt": 50}}
        )

        assert response is not None
        assert isinstance(response, str)

    def test_integration_with_aircraft_state(self):
        """Test ATC controller responds appropriately to aircraft state"""
        from src.atc_controller import ATCController, FlightPhase

        controller = ATCController()

        # Simulate aircraft taking off
        controller.set_aircraft_phase("Viper 1-1", FlightPhase.TAXI)

        # Process takeoff request
        response = controller.process_pilot_request(
            "Viper 1-1",
            "Tower, request takeoff",
            {"speed": 0, "position": {"alt": 50}}
        )

        # Should grant clearance
        assert "cleared for takeoff" in response.lower() or "takeoff" in response.lower()

        # Update state to airborne
        controller.update_aircraft_phase_from_state("Viper 1-1", {
            "speed": 300,
            "position": {"alt": 1000}
        })

        # Phase should now be airborne
        assert controller.get_aircraft_phase("Viper 1-1") == FlightPhase.AIRBORNE

    def test_context_awareness(self):
        """Test that controller maintains context across requests"""
        from src.atc_controller import ATCController

        controller = ATCController()

        # First request
        response1 = controller.process_pilot_request(
            "Viper 1-1",
            "Ground, request startup",
            {"speed": 0, "position": {"alt": 50}}
        )

        # Second request should be aware of first
        response2 = controller.process_pilot_request(
            "Viper 1-1",
            "Ground, request taxi",
            {"speed": 0, "position": {"alt": 50}}
        )

        # Both responses should be valid
        assert response1 is not None
        assert response2 is not None
