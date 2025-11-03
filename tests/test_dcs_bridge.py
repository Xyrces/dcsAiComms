"""
Tests for DCS Export Bridge (UDP listener and aircraft state tracking)

Following TDD methodology - write tests first, then implement.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestDCSBridge:
    """Test suite for DCS Export Bridge UDP listener"""

    def test_bridge_initialization(self):
        """Test that DCS Bridge can be initialized with default port"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge(port=10308)
        assert bridge.port == 10308
        assert bridge.is_running is False
        assert bridge.aircraft_states == {}

    def test_bridge_custom_port(self):
        """Test that DCS Bridge accepts custom port"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge(port=10309)
        assert bridge.port == 10309

    @patch('socket.socket')
    def test_start_creates_udp_socket(self, mock_socket):
        """Test that start() creates a UDP socket"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge(port=10308)
        bridge.start()

        # Should create UDP socket
        mock_socket.assert_called()
        assert bridge.is_running is True

    @patch('socket.socket')
    def test_start_binds_to_port(self, mock_socket):
        """Test that start() binds socket to correct address"""
        from src.dcs_bridge import DCSBridge

        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock

        bridge = DCSBridge(port=10308)
        bridge.start()

        # Should bind to localhost and port
        mock_sock.bind.assert_called_with(('127.0.0.1', 10308))

    @patch('socket.socket')
    def test_stop_closes_socket(self, mock_socket):
        """Test that stop() closes the socket"""
        from src.dcs_bridge import DCSBridge

        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock

        bridge = DCSBridge(port=10308)
        bridge.start()
        bridge.stop()

        mock_sock.close.assert_called()
        assert bridge.is_running is False

    def test_parse_json_valid_data(self):
        """Test parsing valid JSON data from DCS"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        data = {
            "pilot": "Viper 1-1",
            "position": {"lat": 43.2, "lon": 39.8, "alt": 5000},
            "heading": 270,
            "speed": 450,
            "frequency": 251.0
        }
        json_str = json.dumps(data)

        result = bridge.parse_data(json_str)
        assert result["pilot"] == "Viper 1-1"
        assert result["position"]["alt"] == 5000
        assert result["heading"] == 270

    def test_parse_json_invalid_data(self):
        """Test parsing invalid JSON returns None"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        result = bridge.parse_data("invalid json{]")
        assert result is None

    def test_update_aircraft_state(self):
        """Test updating aircraft state"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        data = {
            "pilot": "Viper 1-1",
            "position": {"lat": 43.2, "lon": 39.8, "alt": 5000},
            "heading": 270,
            "speed": 450
        }

        bridge.update_aircraft_state("Viper 1-1", data)

        assert "Viper 1-1" in bridge.aircraft_states
        assert bridge.aircraft_states["Viper 1-1"]["heading"] == 270
        assert bridge.aircraft_states["Viper 1-1"]["speed"] == 450

    def test_get_aircraft_state(self):
        """Test retrieving aircraft state"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        data = {
            "pilot": "Viper 1-1",
            "position": {"lat": 43.2, "lon": 39.8, "alt": 5000},
            "heading": 270,
            "speed": 450
        }

        bridge.update_aircraft_state("Viper 1-1", data)
        state = bridge.get_aircraft_state("Viper 1-1")

        assert state is not None
        assert state["heading"] == 270

    def test_get_aircraft_state_missing(self):
        """Test retrieving non-existent aircraft state returns None"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        state = bridge.get_aircraft_state("Unknown Aircraft")

        assert state is None

    def test_get_all_aircraft_states(self):
        """Test retrieving all aircraft states"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()

        bridge.update_aircraft_state("Viper 1-1", {"pilot": "Viper 1-1", "heading": 270})
        bridge.update_aircraft_state("Viper 1-2", {"pilot": "Viper 1-2", "heading": 280})

        all_states = bridge.get_all_aircraft_states()

        assert len(all_states) == 2
        assert "Viper 1-1" in all_states
        assert "Viper 1-2" in all_states

    def test_process_incoming_data(self):
        """Test processing incoming data updates state"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        json_data = json.dumps({
            "pilot": "Viper 1-1",
            "position": {"lat": 43.2, "lon": 39.8, "alt": 5000},
            "heading": 270,
            "speed": 450,
            "frequency": 251.0
        })

        bridge.process_incoming_data(json_data)

        state = bridge.get_aircraft_state("Viper 1-1")
        assert state is not None
        assert state["heading"] == 270

    def test_process_incoming_data_invalid_json(self):
        """Test processing invalid JSON doesn't crash"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        bridge.process_incoming_data("invalid json{]")

        # Should not raise exception
        assert len(bridge.aircraft_states) == 0

    @patch('threading.Thread')
    def test_start_listener_thread(self, mock_thread):
        """Test that listening starts in background thread"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()

        # Mock the thread creation
        with patch.object(bridge, '_listen_loop'):
            bridge.start()

        # Should create a thread for listening
        assert bridge.is_running is True


class TestAircraftStateTracking:
    """Test suite for aircraft state tracking features"""

    def test_detect_altitude_change(self):
        """Test detecting altitude changes"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()

        # Initial state
        bridge.update_aircraft_state("Viper 1-1", {
            "pilot": "Viper 1-1",
            "position": {"lat": 43.2, "lon": 39.8, "alt": 5000}
        })

        # Updated state
        bridge.update_aircraft_state("Viper 1-1", {
            "pilot": "Viper 1-1",
            "position": {"lat": 43.2, "lon": 39.8, "alt": 10000}
        })

        state = bridge.get_aircraft_state("Viper 1-1")
        assert state["position"]["alt"] == 10000

    def test_detect_speed_change(self):
        """Test detecting speed changes"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()

        bridge.update_aircraft_state("Viper 1-1", {"pilot": "Viper 1-1", "speed": 100})
        bridge.update_aircraft_state("Viper 1-1", {"pilot": "Viper 1-1", "speed": 300})

        state = bridge.get_aircraft_state("Viper 1-1")
        assert state["speed"] == 300

    def test_track_multiple_aircraft(self):
        """Test tracking multiple aircraft simultaneously"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()

        # Add multiple aircraft
        for i in range(1, 5):
            bridge.update_aircraft_state(f"Viper 1-{i}", {
                "pilot": f"Viper 1-{i}",
                "heading": 270 + i * 10,
                "speed": 400 + i * 10
            })

        all_states = bridge.get_all_aircraft_states()
        assert len(all_states) == 4
        assert bridge.get_aircraft_state("Viper 1-3")["heading"] == 300

    def test_clear_aircraft_state(self):
        """Test clearing specific aircraft state"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()

        bridge.update_aircraft_state("Viper 1-1", {"pilot": "Viper 1-1", "heading": 270})
        bridge.update_aircraft_state("Viper 1-2", {"pilot": "Viper 1-2", "heading": 280})

        bridge.clear_aircraft_state("Viper 1-1")

        assert bridge.get_aircraft_state("Viper 1-1") is None
        assert bridge.get_aircraft_state("Viper 1-2") is not None

    def test_clear_all_aircraft_states(self):
        """Test clearing all aircraft states"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()

        bridge.update_aircraft_state("Viper 1-1", {"pilot": "Viper 1-1", "heading": 270})
        bridge.update_aircraft_state("Viper 1-2", {"pilot": "Viper 1-2", "heading": 280})

        bridge.clear_all_aircraft_states()

        assert len(bridge.get_all_aircraft_states()) == 0


class TestDataExtraction:
    """Test suite for extracting specific data from aircraft state"""

    def test_extract_position_data(self):
        """Test extracting position data"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        bridge.update_aircraft_state("Viper 1-1", {
            "pilot": "Viper 1-1",
            "position": {"lat": 43.2, "lon": 39.8, "alt": 5000}
        })

        position = bridge.get_aircraft_position("Viper 1-1")
        assert position is not None
        assert position["lat"] == 43.2
        assert position["lon"] == 39.8
        assert position["alt"] == 5000

    def test_extract_position_missing_aircraft(self):
        """Test extracting position from missing aircraft returns None"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        position = bridge.get_aircraft_position("Unknown")
        assert position is None

    def test_extract_heading(self):
        """Test extracting heading data"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        bridge.update_aircraft_state("Viper 1-1", {
            "pilot": "Viper 1-1",
            "heading": 270
        })

        heading = bridge.get_aircraft_heading("Viper 1-1")
        assert heading == 270

    def test_extract_heading_missing_aircraft(self):
        """Test extracting heading from missing aircraft returns None"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        heading = bridge.get_aircraft_heading("Unknown")
        assert heading is None

    def test_extract_speed(self):
        """Test extracting speed data"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        bridge.update_aircraft_state("Viper 1-1", {
            "pilot": "Viper 1-1",
            "speed": 450
        })

        speed = bridge.get_aircraft_speed("Viper 1-1")
        assert speed == 450

    def test_extract_frequency(self):
        """Test extracting frequency data"""
        from src.dcs_bridge import DCSBridge

        bridge = DCSBridge()
        bridge.update_aircraft_state("Viper 1-1", {
            "pilot": "Viper 1-1",
            "frequency": 251.0
        })

        freq = bridge.get_aircraft_frequency("Viper 1-1")
        assert freq == 251.0
