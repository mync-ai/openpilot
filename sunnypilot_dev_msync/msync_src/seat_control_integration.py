#!/usr/bin/env python3
"""
Seat Control Integration Module

This module integrates the seat control system with the sunnypilot UI
by publishing seat control commands to the messaging system.
"""

import time
import threading
from cereal import messaging
from sunnypilot_dev_msync.msync_src.op_translator import execute_control


class SeatControlPublisher:
    """Publishes seat control commands to the messaging system for UI display."""

    def __init__(self, decider, submaster, update_frequency=10):  # 10 Hz update rate
        self.update_frequency = update_frequency
        self.pm = messaging.PubMaster(['seatControl'])
        self.running = False
        self.thread = None
        self.decider = decider
        self.submaster = submaster

        # Command mapping from string to enum
        self.command_map = {
            'NEUTRAL': 'neutral',
            'MILD_FORWARD': 'mildForward',
            'MILD_BACK': 'mildBack',
            'HARD_FORWARD': 'hardForward',
            'HARD_BACK': 'hardBack',
            'MILD_LEFT': 'mildLeft',
            'MILD_RIGHT': 'mildRight',
            'HARD_LEFT': 'hardLeft',
            'HARD_RIGHT': 'hardRight'
        }

    def start(self):
        """Start the seat control publisher thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the seat control publisher thread."""
        self.running = False
        if self.thread:
            self.thread.join()

    def _run(self):
        """Main publisher loop."""
        latency = 1.0 / self.update_frequency

        # Use the passed submaster instead of creating a new one
        interesting_subs = ['modelV2', 'carState']

        try:
            for control_response in execute_control(self.decider, self.submaster, interesting_subs, latency):
                if not self.running:
                    break

                # Create and publish seat control message
                seat_control_msg = messaging.new_message('seatControl')

                # Handle tuple return: (lateral_command_str, longitudinal_command_str)
                lateral_command_str = control_response[0]
                longitudinal_command_str = control_response[1]

                # Map command strings to enums
                lateral_command_enum = self.command_map.get(lateral_command_str, 'neutral')
                longitudinal_command_enum = self.command_map.get(longitudinal_command_str, 'neutral')

                seat_control_msg.seatControl.lateralCommand = lateral_command_enum
                seat_control_msg.seatControl.longitudinalCommand = longitudinal_command_enum
                seat_control_msg.seatControl.timestamp = int(time.time() * 1e9)  # nanoseconds

                self.pm.send('seatControl', seat_control_msg)

        except Exception as e:
            print(f"Seat control publisher error: {e}")


def start_seat_control_publisher(publisher):
    """Start the seat control publisher."""
    publisher.start()


def stop_seat_control_publisher(publisher):
    """Stop the seat control publisher."""
    publisher.stop()


if __name__ == "__main__":
    # Test the publisher
    publisher = SeatControlPublisher()
    publisher.start()

    try:
        # Run for 30 seconds
        time.sleep(30)
    finally:
        publisher.stop()
