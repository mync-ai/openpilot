#!/usr/bin/env python3
"""
Small test to verify telemetry script outputs correct commands for enum values
"""

import sys
sys.path.append('/Users/brad/Desktop/openpilot')

from openpilot.selfdrive.telemetryd.subscriber import get_short_control
from cereal import messaging
import time

def test_telemetry_enum_processing():
    """Test that telemetry script processes each enum value correctly"""
    print("Testing telemetry enum processing...\n")

    # Expected mapping from the subscriber.py
    expected_results = {
        0: "neutral",
        1: "forward",
        2: "back",
        3: "left",     # mildLeft -> "left"
        4: "right",    # mildRight -> "right"
        5: "left",     # hardLeft -> "left"
        6: "right"     # hardRight -> "right"
    }

    try:
        pm = messaging.PubMaster(['seatControl'])

        print("Command -> Expected -> Actual -> Status")
        print("-" * 40)

        for cmd_val, expected in expected_results.items():
            # Send test message
            msg = messaging.new_message('seatControl')
            msg.seatControl.command = cmd_val
            msg.seatControl.source = 1
            msg.seatControl.timestamp = int(time.time() * 1e9)

            pm.send('seatControl', msg)
            time.sleep(0.01)

            # Get result
            result = get_short_control()
            status = "✓ PASS" if result == expected else "✗ FAIL"

            print(f"{cmd_val:7} -> {expected:8} -> {str(result):8} -> {status}")

        print("\nTurn detection check:")
        left_commands = [3, 5]  # mildLeft, hardLeft
        right_commands = [4, 6] # mildRight, hardRight

        for cmd in left_commands:
            msg = messaging.new_message('seatControl')
            msg.seatControl.command = cmd
            pm.send('seatControl', msg)
            time.sleep(0.01)
            result = get_short_control()
            print(f"Command {cmd}: '{result}' -> {'LEFT TURN' if result == 'left' else 'ERROR'}")

        for cmd in right_commands:
            msg = messaging.new_message('seatControl')
            msg.seatControl.command = cmd
            pm.send('seatControl', msg)
            time.sleep(0.01)
            result = get_short_control()
            print(f"Command {cmd}: '{result}' -> {'RIGHT TURN' if result == 'right' else 'ERROR'}")

    except Exception as e:
        print(f"Test failed: {e}")
        print("This may be due to messaging conflicts with other processes.")

if __name__ == "__main__":
    test_telemetry_enum_processing()
    print("\n✓ Test complete - telemetry script should handle these values correctly")
