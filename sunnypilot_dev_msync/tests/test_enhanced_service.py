#!/usr/bin/env python3
"""
Test the enhanced seat control service with configuration management.
"""

import sys
import os
import time
import subprocess
import threading

# Add the openpilot root to the path - handle both direct run and tests/ directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir.endswith('tests'):
    # Running from tests/ directory
    openpilot_root = os.path.abspath(os.path.join(current_dir, '../../../..'))
else:
    # Running from msync_src/ directory
    openpilot_root = os.path.abspath(os.path.join(current_dir, '../../..'))

sys.path.insert(0, openpilot_root)

from sunnypilot_dev_msync.msync_src.seat_control_service_enhanced import EnhancedSeatControlService
from sunnypilot_dev_msync.msync_src.config_client import send_config_request


def test_service_standalone():
    """Test the service in standalone mode."""
    print("=== Testing Enhanced Seat Control Service ===")

    # Create service with initial config
    initial_config = {
        'frequency': 15,
        'turn_thresh_1': 0.8,
        'turn_thresh_2': 2.0,
        'long_thresh': 0.8,
        'smoothing_window': 3,
        'horizon': 2.5,
        'use_plan': False
    }

    print(f"Creating service with initial config: {initial_config}")
    service = EnhancedSeatControlService(initial_config=initial_config)

    # Start service in a separate thread
    service_thread = threading.Thread(target=service.start, daemon=True)
    service_thread.start()

    print("Service started, waiting a moment for initialization...")
    time.sleep(2)

    try:
        # Test 1: Get current configuration
        print("\n--- Test 1: Get Configuration ---")
        config = send_config_request('get')
        if config:
            print("✅ Get config successful")
        else:
            print("❌ Get config failed")

        # Test 2: Set new configuration
        print("\n--- Test 2: Set Configuration ---")
        new_config = {
            'frequency': 25,
            'turn_thresh_1': 1.2,
            'turn_thresh_2': 3.0,
            'long_thresh': 1.2,
            'smoothing_window': 5,
            'horizon': 3.5,
            'use_plan': True
        }

        config = send_config_request('set', new_config)
        if config and config['frequency'] == 25:
            print("✅ Set config successful")
        else:
            print("❌ Set config failed")

        # Test 3: Reset to defaults
        print("\n--- Test 3: Reset Configuration ---")
        config = send_config_request('reset')
        if config:
            print("✅ Reset config successful")
            print(f"Default config: {config}")
        else:
            print("❌ Reset config failed")

        # Test 4: Set invalid configuration
        print("\n--- Test 4: Invalid Configuration ---")
        invalid_config = {
            'frequency': 200,  # Invalid: too high
            'turn_thresh_1': 1.0,
            'turn_thresh_2': 2.5,
            'long_thresh': 1.0,
            'smoothing_window': 4,
            'horizon': 3.0,
            'use_plan': False
        }

        config = send_config_request('set', invalid_config)
        if config and config['frequency'] != 200:
            print("✅ Invalid config correctly rejected")
        else:
            print("❌ Invalid config was accepted")

    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        print("\nStopping service...")
        service.stop()

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_service_standalone()
