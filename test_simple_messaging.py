#!/usr/bin/env python3
# filepath: /Users/brad/Desktop/openpilot/test_simple_messaging.py

import time
from cereal import messaging

def test_messaging_availability():
    """Test which seat control topics are available for publishing."""

    topics_to_test = ['seatControl']

    for topic in topics_to_test:
        try:
            print(f"Testing {topic}...")
            pm = messaging.PubMaster([topic])
            print(f"  ✓ {topic} - Available for publishing")
            pm = None  # Clean up
        except Exception as e:
            print(f"  ✗ {topic} - BLOCKED: {e}")

    print("\nTesting subscribers...")
    for topic in topics_to_test:
        try:
            sm = messaging.SubMaster([topic])
            print(f"  ✓ {topic} - Available for subscribing")
        except Exception as e:
            print(f"  ✗ {topic} - Subscriber failed: {e}")

if __name__ == "__main__":
    test_messaging_availability()