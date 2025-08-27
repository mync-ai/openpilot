#!/usr/bin/env python3
"""Test script to verify the sticky parameter fix."""

import sys
sys.path.append('/Users/brad/Desktop/openpilot')

from sunnypilot_dev_msync.msync_src.short_control import Decider

def test_sticky_behavior():
    """Test that the seat control returns to neutral after sticky commands."""

    # Create decider with small sticky values for testing
    decider = Decider(
        long_sens=2,      # Quick response when neutral
        lat_sens=2,       # Quick response when neutral
        long_sticky=5,    # Sticky when active
        lat_sticky=5,     # Sticky when active
        turn_thresh_1=0.5,
        turn_thresh_2=1.0
    )

    # Mock data structure
    class MockData:
        def __init__(self, accel_x=None, accel_y=None, vel_x=None, vel_y=None):
            self.x = accel_x or [0.0] * 10
            self.y = accel_y or [0.0] * 10

    # Test scenario: mild left turn followed by neutral
    print("Testing sticky behavior fix...")
    print("Initial state:", decider.short_decision())

    # Step 1: Send mild left signal (accel_y > turn_thresh_1)
    print("\n--- Sending mild left signal ---")
    for i in range(3):
        mock_data = {
            'acceleration_pred': MockData(accel_y=[0.8] * 10),  # Above turn_thresh_1
            'velocity_pred': MockData(),
            'left_blinker': 0,
            'right_blinker': 0,
            'vEgo': 10.0,
            'aEgo': 0.0,
            'gear_shifter': 'drive'
        }
        decider.set_data(mock_data)
        result = decider.short_decision()
        print(f"Step {i+1}: {result}, lat_state={decider.lat_state}, lat_history={list(decider._lat_history)}")

    # Step 2: Send neutral signal (should return to neutral after sens window)
    print("\n--- Sending neutral signal ---")
    for i in range(8):  # More than enough steps to clear both sens and sticky windows
        mock_data = {
            'acceleration_pred': MockData(accel_y=[0.0] * 10),  # Neutral
            'velocity_pred': MockData(),
            'left_blinker': 0,
            'right_blinker': 0,
            'vEgo': 10.0,
            'aEgo': 0.0,
            'gear_shifter': 'drive'
        }
        decider.set_data(mock_data)
        result = decider.short_decision()
        print(f"Step {i+1}: {result}, lat_state={decider.lat_state}, lat_history={list(decider._lat_history)}")

        if result[0] == 'NEUTRAL':
            print(f"✅ Successfully returned to NEUTRAL after {i+1} steps!")
            break
    else:
        print("❌ Failed to return to NEUTRAL")

    print(f"\nFinal state: {decider.short_decision()}")

if __name__ == '__main__':
    test_sticky_behavior()
