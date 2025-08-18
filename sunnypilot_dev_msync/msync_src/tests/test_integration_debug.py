#!/usr/bin/env python3
"""Isolate the seat control integration error."""

import sys
import traceback
sys.path.insert(0, '/home/kerrb/msync_branching/openpilot')

from cereal import messaging
from sunnypilot_dev_msync.msync_src.short_control import Decider
from sunnypilot_dev_msync.msync_src.parameter_manager import SeatControlParameterManager


def test_integration_step_by_step():
    """Test each step of the integration to isolate the error."""

    print("Step 1: Testing Decider creation...")
    try:
        pm = SeatControlParameterManager()
        config = pm.get_current_config()
        print(f"Config: {config}")

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
        print("✓ Decider created successfully")
    except Exception as e:
        print(f"✗ Decider creation failed: {e}")
        traceback.print_exc()
        return False

    print("\\nStep 2: Testing short_decision...")
    try:
        from types import SimpleNamespace
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
        print(f"✓ short_decision returned: {result}")
    except Exception as e:
        print(f"✗ short_decision failed: {e}")
        traceback.print_exc()
        return False

    print("\\nStep 3: Testing message creation...")
    try:
        msg = messaging.new_message('seatControl')
        print("✓ Message created successfully")
    except Exception as e:
        print(f"✗ Message creation failed: {e}")
        traceback.print_exc()
        return False

    print("\\nStep 4: Testing enum assignment...")
    try:
        lateral_cmd, longitudinal_cmd = result

        command_map = {
            'NEUTRAL': 'neutral',
            'FORWARD': 'forward',
            'BACK': 'back',
            'MILD_LEFT': 'mildLeft',
            'MILD_RIGHT': 'mildRight',
            'HARD_LEFT': 'hardLeft',
            'HARD_RIGHT': 'hardRight'
        }

        lateral_enum = command_map.get(lateral_cmd, 'neutral')
        longitudinal_enum = command_map.get(longitudinal_cmd, 'neutral')

        print(f"Mapping: {lateral_cmd} -> {lateral_enum}, {longitudinal_cmd} -> {longitudinal_enum}")

        msg.seatControl.lateralCommand = lateral_enum
        msg.seatControl.longitudinalCommand = longitudinal_enum
        print("✓ Enum assignment successful")
    except Exception as e:
        print(f"✗ Enum assignment failed: {e}")
        traceback.print_exc()
        return False

    print("\\nStep 5: Testing timestamp assignment...")
    try:
        import time
        msg.seatControl.timestamp = int(time.time() * 1e9)
        print("✓ Timestamp assignment successful")
    except Exception as e:
        print(f"✗ Timestamp assignment failed: {e}")
        traceback.print_exc()
        return False

    print("\\nStep 6: Testing message send...")
    try:
        pm = messaging.PubMaster(['seatControl'])
        pm.send('seatControl', msg)
        print("✓ Message send successful")
    except Exception as e:
        print(f"✗ Message send failed: {e}")
        traceback.print_exc()
        return False

    print("\\n✅ All integration steps passed!")
    return True


if __name__ == "__main__":
    test_integration_step_by_step()
