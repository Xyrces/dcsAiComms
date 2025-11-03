"""
DCS Export Bridge - UDP Listener for DCS World Data

This module handles receiving data from DCS World via Export.lua,
parsing the JSON data, and tracking aircraft state in real-time.

Author: DCS Natural Language ATC Project
"""

import socket
import json
import logging
import threading
from typing import Dict, Optional, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class DCSBridge:
    """
    UDP listener that receives and processes data from DCS World Export.lua.

    Receives JSON data containing aircraft state (position, heading, speed, etc.)
    and maintains a real-time state database for all tracked aircraft.
    """

    def __init__(self, port: int = 10308, host: str = '127.0.0.1'):
        """
        Initialize the DCS Export Bridge.

        Args:
            port: UDP port to listen on (default: 10308)
            host: Host address to bind to (default: localhost)
        """
        self.port = port
        self.host = host
        self.socket = None
        self.is_running = False
        self.listener_thread = None
        self.aircraft_states: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()  # Thread-safe state access

        logger.info(f"DCS Bridge initialized on {host}:{port}")

    def start(self) -> bool:
        """
        Start the UDP listener.

        Creates a UDP socket, binds to the configured port,
        and starts listening for incoming data in a background thread.

        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("DCS Bridge is already running")
            return True

        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.settimeout(1.0)  # 1 second timeout for clean shutdown

            # Bind to port
            self.socket.bind((self.host, self.port))
            self.is_running = True

            # Start listener thread
            self.listener_thread = threading.Thread(
                target=self._listen_loop,
                daemon=True,
                name="DCS-Bridge-Listener"
            )
            self.listener_thread.start()

            logger.info(f"DCS Bridge started, listening on {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start DCS Bridge: {e}")
            self.is_running = False
            return False

    def stop(self) -> bool:
        """
        Stop the UDP listener and close the socket.

        Returns:
            bool: True if stopped successfully
        """
        if not self.is_running:
            logger.warning("DCS Bridge is not running")
            return True

        self.is_running = False

        # Wait for listener thread to finish
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2.0)

        # Close socket
        if self.socket:
            try:
                self.socket.close()
                logger.info("DCS Bridge stopped")
            except Exception as e:
                logger.error(f"Error closing socket: {e}")

        return True

    def _listen_loop(self):
        """
        Background thread that continuously listens for UDP data.

        This runs in a separate thread and processes incoming data packets.
        """
        logger.info("DCS Bridge listener thread started")

        while self.is_running:
            try:
                # Receive data (with timeout for clean shutdown)
                data, addr = self.socket.recvfrom(4096)  # 4KB buffer
                data_str = data.decode('utf-8')

                # Process the incoming data
                self.process_incoming_data(data_str)

            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                if self.is_running:  # Only log if we're supposed to be running
                    logger.error(f"Error in listener loop: {e}")

        logger.info("DCS Bridge listener thread stopped")

    def parse_data(self, data_str: str) -> Optional[Dict]:
        """
        Parse JSON data string from DCS Export.lua.

        Args:
            data_str: JSON string containing aircraft data

        Returns:
            Parsed dictionary or None if invalid
        """
        try:
            data = json.loads(data_str)
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing data: {e}")
            return None

    def process_incoming_data(self, data_str: str):
        """
        Process incoming JSON data and update aircraft state.

        Args:
            data_str: JSON string containing aircraft data
        """
        data = self.parse_data(data_str)
        if data is None:
            return

        # Extract pilot/callsign identifier
        pilot = data.get('pilot')
        if not pilot:
            logger.warning("Received data without pilot identifier")
            return

        # Update aircraft state
        self.update_aircraft_state(pilot, data)

    def update_aircraft_state(self, callsign: str, data: Dict[str, Any]):
        """
        Update the state of a specific aircraft.

        Thread-safe update of aircraft state dictionary.

        Args:
            callsign: Aircraft callsign/pilot identifier
            data: Dictionary containing aircraft state data
        """
        with self._lock:
            # Add timestamp
            data['last_updated'] = datetime.now().isoformat()

            # Update or create aircraft state
            if callsign in self.aircraft_states:
                # Update existing state
                self.aircraft_states[callsign].update(data)
            else:
                # Create new state
                self.aircraft_states[callsign] = data

            logger.debug(f"Updated state for {callsign}")

    def get_aircraft_state(self, callsign: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a specific aircraft.

        Args:
            callsign: Aircraft callsign/pilot identifier

        Returns:
            Dictionary containing aircraft state or None if not found
        """
        with self._lock:
            return self.aircraft_states.get(callsign)

    def get_all_aircraft_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the current state of all tracked aircraft.

        Returns:
            Dictionary mapping callsigns to aircraft states
        """
        with self._lock:
            return self.aircraft_states.copy()

    def clear_aircraft_state(self, callsign: str) -> bool:
        """
        Clear the state of a specific aircraft.

        Args:
            callsign: Aircraft callsign/pilot identifier

        Returns:
            True if aircraft was found and cleared, False otherwise
        """
        with self._lock:
            if callsign in self.aircraft_states:
                del self.aircraft_states[callsign]
                logger.info(f"Cleared state for {callsign}")
                return True
            return False

    def clear_all_aircraft_states(self):
        """Clear all aircraft states."""
        with self._lock:
            count = len(self.aircraft_states)
            self.aircraft_states.clear()
            logger.info(f"Cleared all aircraft states ({count} aircraft)")

    # Convenience methods for extracting specific data

    def get_aircraft_position(self, callsign: str) -> Optional[Dict[str, float]]:
        """
        Get the position of a specific aircraft.

        Args:
            callsign: Aircraft callsign/pilot identifier

        Returns:
            Dictionary with lat, lon, alt or None if not found
        """
        state = self.get_aircraft_state(callsign)
        if state:
            return state.get('position')
        return None

    def get_aircraft_heading(self, callsign: str) -> Optional[float]:
        """
        Get the heading of a specific aircraft.

        Args:
            callsign: Aircraft callsign/pilot identifier

        Returns:
            Heading in degrees or None if not found
        """
        state = self.get_aircraft_state(callsign)
        if state:
            return state.get('heading')
        return None

    def get_aircraft_speed(self, callsign: str) -> Optional[float]:
        """
        Get the speed of a specific aircraft.

        Args:
            callsign: Aircraft callsign/pilot identifier

        Returns:
            Speed in knots or None if not found
        """
        state = self.get_aircraft_state(callsign)
        if state:
            return state.get('speed')
        return None

    def get_aircraft_frequency(self, callsign: str) -> Optional[float]:
        """
        Get the radio frequency of a specific aircraft.

        Args:
            callsign: Aircraft callsign/pilot identifier

        Returns:
            Frequency in MHz or None if not found
        """
        state = self.get_aircraft_state(callsign)
        if state:
            return state.get('frequency')
        return None


if __name__ == '__main__':
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    bridge = DCSBridge(port=10308)
    bridge.start()

    print("DCS Bridge running. Press Ctrl+C to stop...")
    try:
        while True:
            import time
            time.sleep(1)

            # Print current aircraft states
            states = bridge.get_all_aircraft_states()
            if states:
                print(f"\nTracking {len(states)} aircraft:")
                for callsign, state in states.items():
                    pos = state.get('position', {})
                    print(f"  {callsign}: Alt={pos.get('alt', 'N/A')} "
                          f"Hdg={state.get('heading', 'N/A')} "
                          f"Spd={state.get('speed', 'N/A')}")

    except KeyboardInterrupt:
        print("\nStopping DCS Bridge...")
        bridge.stop()
