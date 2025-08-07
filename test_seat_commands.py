#!/usr/bin/env python3
"""
Simple test to print seat control commands from subscriber.py
Run this while openpilot replay and seat control service are running.
"""

import sys
import time

# Add openpilot to path
sys.path.append('/Users/brad/Desktop/openpilot')

from openpilot.selfdrive.telemetryd.subscriber import get_short_control

def test_seat_control():
    print("Testing seat control output...")
    print("Press Ctrl+C to stop")
    print("-" * 40)
    
    try:
        while True:
            result = get_short_control()
            if result:
                print(f"Returned: {result}")
            else:
                print("No seat control data")
            time.sleep(0.2)  # Check every 200ms
            
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    test_seat_control()
