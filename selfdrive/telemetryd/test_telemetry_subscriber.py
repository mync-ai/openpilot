#!/usr/bin/env python3
"""
Test script for polling subscriber.py functions every second.
Tests GPS, IMU, and seat control data retrieval.
"""

import time
import sys
from subscriber import get_gps, get_imu, get_short_control

def print_separator():
    """Print a visual separator between polling cycles."""
    print("=" * 80)

def test_gps():
    """Test GPS data retrieval."""
    print("=== GPS Data ===")
    try:
        gps_data = get_gps()
        if gps_data:
            print(f"GPS: {gps_data}")
        else:
            print("GPS: No data available")
    except Exception as e:
        print(f"GPS Error: {e}")
    print()

def test_imu():
    """Test IMU data retrieval."""
    print("=== IMU Data ===")
    try:
        imu_data = get_imu()
        if imu_data:
            print(f"IMU: {imu_data}")
        else:
            print("IMU: No data available")
    except Exception as e:
        print(f"IMU Error: {e}")
    print()

def test_seat_control():
    """Test seat control data retrieval."""
    print("=== Seat Control Data ===")
    try:
        lat_cmd, long_cmd = get_short_control()
        if lat_cmd != "N/A" and long_cmd != "N/A":
            msg = lat_cmd + " " + long_cmd
        else:
            msg = "_ _"
        print("<timestamp> " + msg)
    except Exception as e:
        print(f"Seat Control Error: {e}")
    print()

def main():
    """Main polling loop that tests all subscriber functions every second."""
    print("Starting telemetry subscriber test...")
    print("Polling GPS, IMU, and seat control data every second")
    print("Press Ctrl+C to stop\n")

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            print(f"Polling Cycle #{cycle_count} - {time.strftime('%H:%M:%S')}")
            print_separator()

            # Test all subscriber functions
            test_gps()
            test_imu()
            test_seat_control()

            print_separator()
            print(f"Cycle #{cycle_count} complete. Waiting 1 second...\n")

            # Wait 1 second before next poll
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nTest stopped by user")
        print(f"Completed {cycle_count} polling cycles")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


