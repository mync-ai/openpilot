#!/usr/bin/env python3
"""
Test script for the log analyzer.

This script tests the analyze_logs.py functionality with sample data
or real log files if available.
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

# Add the openpilot root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sunnypilot_dev_msync.logging.analyze_logs import LogAnalyzer, SeatControlTracker


class TestSeatControlTracker(unittest.TestCase):
    """Test the SeatControlTracker class."""

    def setUp(self):
        self.tracker = SeatControlTracker()

    def test_initial_state(self):
        """Test initial state of tracker."""
        self.assertIsNone(self.tracker.current_command)
        self.assertIsNone(self.tracker.command_start_time)
        self.assertEqual(len(self.tracker.command_durations), 0)

    def test_first_command(self):
        """Test setting the first command."""
        result = self.tracker.update(1000000000, 'FORWARD', 'ACCELERATE')
        self.assertIsNone(result)  # No previous command to report duration for
        self.assertEqual(self.tracker.current_command, 'FORWARD')
        self.assertEqual(self.tracker.command_start_time, 1000000000)

    def test_command_change_duration(self):
        """Test command change and duration calculation."""
        # Set first command
        self.tracker.update(1000000000, 'FORWARD', 'ACCELERATE')

        # Change command after 500ms
        result = self.tracker.update(1500000000, 'NEUTRAL', 'STOP')

        self.assertIsNotNone(result)
        self.assertEqual(result['previous_command'], 'FORWARD')
        self.assertEqual(result['duration_ms'], 500.0)
        self.assertEqual(result['end_timestamp'], 1500000000)

        # Check new state
        self.assertEqual(self.tracker.current_command, 'NEUTRAL')
        self.assertEqual(self.tracker.command_start_time, 1500000000)
        self.assertEqual(len(self.tracker.command_durations), 1)

    def test_same_command_no_duration(self):
        """Test that same command doesn't trigger duration calculation."""
        self.tracker.update(1000000000, 'FORWARD', 'ACCELERATE')
        result = self.tracker.update(1100000000, 'FORWARD', 'ACCELERATE')

        self.assertIsNone(result)
        self.assertEqual(self.tracker.current_command, 'FORWARD')
        self.assertEqual(self.tracker.command_start_time, 1000000000)


class TestLogAnalyzer(unittest.TestCase):
    """Test the LogAnalyzer class."""

    def setUp(self):
        self.analyzer = LogAnalyzer("/fake/path", ['modelV2', 'carState'], max_messages=10)

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Test nanosecond timestamp conversion
        timestamp_ns = 1640995200123456789  # 2022-01-01 00:00:00.123456789
        formatted = self.analyzer.format_timestamp(timestamp_ns)

        # Should be in HH:MM:SS.mmm format
        self.assertRegex(formatted, r'\d{2}:\d{2}:\d{2}\.\d{3}')

    def test_message_counters(self):
        """Test message counting functionality."""
        self.assertEqual(self.analyzer.total_messages, 0)
        self.assertEqual(len(self.analyzer.message_counts), 0)

    def test_seat_tracker_integration(self):
        """Test that seat tracker is properly integrated."""
        self.assertIsInstance(self.analyzer.seat_tracker, SeatControlTracker)


def create_mock_message(msg_type, timestamp, **kwargs):
    """Create a mock message for testing."""
    msg = Mock()
    msg.which.return_value = msg_type
    msg.logMonoTime = timestamp

    # Add message-specific attributes
    if msg_type == 'carState':
        car_state = Mock()
        car_state.vEgo = kwargs.get('vEgo', 10.0)
        car_state.aEgo = kwargs.get('aEgo', 0.5)
        car_state.steeringAngleDeg = kwargs.get('steeringAngleDeg', 0.0)
        car_state.steeringTorque = kwargs.get('steeringTorque', 0.0)
        car_state.gas = kwargs.get('gas', 0.0)
        car_state.brake = kwargs.get('brake', 0.0)
        car_state.leftBlinker = kwargs.get('leftBlinker', False)
        car_state.rightBlinker = kwargs.get('rightBlinker', False)
        car_state.gearShifter = kwargs.get('gearShifter', 'drive')
        msg.carState = car_state

    elif msg_type == 'seatControl':
        seat_control = Mock()
        seat_control.command = kwargs.get('command', 'neutral')
        seat_control.source = kwargs.get('source', 'none')
        seat_control.timestamp = kwargs.get('timestamp', timestamp)
        msg.seatControl = seat_control

    return msg


class TestMessageFormatting(unittest.TestCase):
    """Test message formatting functions."""

    def setUp(self):
        self.analyzer = LogAnalyzer("/fake/path", ['carState', 'seatControl'])

    def test_format_carstate_message(self):
        """Test carState message formatting."""
        msg = create_mock_message('carState', 1000000000, vEgo=15.5, aEgo=1.2)
        formatted = self.analyzer.format_message(msg)

        self.assertIsNotNone(formatted)
        self.assertIn('CARSTATE', formatted)
        self.assertIn('vEgo: 15.50 m/s', formatted)
        self.assertIn('aEgo: 1.20 m/s²', formatted)

    def test_format_seatcontrol_message(self):
        """Test seatControl message formatting."""
        msg = create_mock_message('seatControl', 1000000000,
                                command='forward', source='accelerate')
        formatted = self.analyzer.format_message(msg)

        self.assertIsNotNone(formatted)
        self.assertIn('SEATCONTROL', formatted)
        self.assertIn('command: forward', formatted)
        self.assertIn('source: accelerate', formatted)

    def test_filtered_message(self):
        """Test that unfiltered messages return None."""
        # Create analyzer that only looks at carState
        analyzer = LogAnalyzer("/fake/path", ['carState'])

        # Try to format a seatControl message
        msg = create_mock_message('seatControl', 1000000000)
        formatted = analyzer.format_message(msg)

        self.assertIsNone(formatted)


def run_manual_test():
    """Manual test function to verify the script works with real data."""
    print("Running manual test of analyze_logs.py...")

    # Test with a small number of messages
    from sunnypilot_dev_msync.logging.analyze_logs import LogAnalyzer

    # You can replace this with a real log path for testing
    test_log_path = "demo_route|2023-01-01--12-00-00"  # This would need to be a real route

    try:
        analyzer = LogAnalyzer(test_log_path, ['carState', 'seatControl'], max_messages=5)
        print(f"Created analyzer for: {test_log_path}")
        print("This would analyze the log if it existed...")
        # analyzer.analyze()  # Uncomment when you have a real log file
    except Exception as e:
        print(f"Expected error (no real log file): {e}")


if __name__ == "__main__":
    print("Testing Log Analyzer Components...")

    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)

    print("\n" + "="*50)
    run_manual_test()
