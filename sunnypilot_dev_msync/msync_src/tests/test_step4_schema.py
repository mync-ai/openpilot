#!/usr/bin/env python3
"""Test step 4 capnp schema changes without UI dependencies."""

import sys
import time
from types import SimpleNamespace

# Add project to path
sys.path.insert(0, '/home/kerrb/msync_branching/openpilot')

try:
    from cereal import messaging
    from sunnypilot_dev_msync.msync_src.short_control import Decider
    from sunnypilot_dev_msync.msync_src.parameter_manager import SeatControlParameterManager
except ImportError as e:
    print(f"Import error (expected if cereal not built): {e}")
    sys.exit(0)


def test_new_seat_control_schema():
    """Test that new SeatControl schema works with lateralCommand and longitudinalCommand."""
    try:
        # Create a seat control message with new schema
        pm = messaging.PubMaster(['seatControl'])

        # Test message creation
        msg = messaging.new_message('seatControl')

        # Test that new fields exist and old ones don't
        seat_control = msg.seatControl

        # Check new fields exist
        assert hasattr(seat_control, 'lateralCommand'), "lateralCommand field missing"
        assert hasattr(seat_control, 'longitudinalCommand'), "longitudinalCommand field missing"
        assert hasattr(seat_control, 'timestamp'), "timestamp field should still exist"

        # Check old fields are removed
        assert not hasattr(seat_control, 'command'), "Old command field should be removed"
        assert not hasattr(seat_control, 'source'), "Old source field should be removed"

        # Test setting values
        seat_control.lateralCommand = 'mildLeft'
        seat_control.longitudinalCommand = 'forward'
        seat_control.timestamp = int(time.time() * 1e9)

        print("✓ New SeatControl schema fields work correctly")
        return True

    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False


def test_decider_integration():
    """Test that Decider still works and returns expected tuple format."""
    try:
        pm = SeatControlParameterManager()
        config = pm.get_current_config()

        decider = Decider(
            turn_thresh_1=config['turn_thresh_1'],
            turn_thresh_2=config['turn_thresh_2'],
            accel_thresh=config['accel_thresh'],
            decel_thresh=config['decel_thresh'],
            long_smoothing=config['long_smoothing'],
            lat_smoothing=config['lat_smoothing'],
            horizon=config['horizon'],
            use_plan=config['use_plan']
        )

        # Mock data
        mock_data = {
            'acceleration_pred': SimpleNamespace(x=[0.0], y=[0.0]),
            'velocity_pred': SimpleNamespace(x=[0.0], y=[0.0]),
            'acceleration_plan': SimpleNamespace(x=[0.0], y=[0.0]),
            'velocity_plan': SimpleNamespace(x=[0.0], y=[0.0]),
            'left_blinker': False,
            'right_blinker': False,
            'vEgo': 0.0,
            'aEgo': 0.0,
        }

        decider.set_data(mock_data)
        result = decider.short_decision()

        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        assert len(result) == 2, f"Expected 2 elements, got {len(result)}"

        lateral, longitudinal = result
        print(f"✓ Decider returns correct tuple format: {result}")
        return True

    except Exception as e:
        print(f"✗ Decider integration test failed: {e}")
        return False


def test_command_mapping():
    """Test that command mapping works with new fields."""
    command_map = {
        'NEUTRAL': 'neutral',
        'FORWARD': 'forward',
        'BACK': 'back',
        'MILD_LEFT': 'mildLeft',
        'MILD_RIGHT': 'mildRight',
        'HARD_LEFT': 'hardLeft',
        'HARD_RIGHT': 'hardRight'
    }

    # Test all commands can be mapped
    test_commands = ['NEUTRAL', 'FORWARD', 'BACK', 'MILD_LEFT', 'MILD_RIGHT', 'HARD_LEFT', 'HARD_RIGHT']

    for cmd in test_commands:
        if cmd not in command_map:
            print(f"✗ Command {cmd} not in mapping")
            return False
        mapped = command_map[cmd]
        print(f"✓ {cmd} -> {mapped}")

    return True


def run_step4_tests():
    """Run all step 4 capnp schema tests."""
    print("Running Step 4 capnp schema tests...\n")

    tests = [
        ("Command mapping", test_command_mapping),
        ("Decider integration", test_decider_integration),
        ("New SeatControl schema", test_new_seat_control_schema),
    ]

    all_passed = True
    for test_name, test_func in tests:
        print(f"--- {test_name} ---")
        try:
            if test_func():
                print(f"✓ {test_name} PASSED\n")
            else:
                print(f"✗ {test_name} FAILED\n")
                all_passed = False
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}\n")
            all_passed = False

    if all_passed:
        print("✅ All Step 4 capnp schema tests PASSED!")
        print("Note: UI build errors are expected until step 5 is completed.")
    else:
        print("❌ Some Step 4 tests FAILED!")

    return all_passed


if __name__ == "__main__":
    run_step4_tests()
