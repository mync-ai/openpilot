#!/usr/bin/env python3
"""
Simple test to verify messaging connectivity between publisher and subscriber.
"""

import time
import threading
import cereal.messaging as messaging


def publisher_test():
    """Test publisher that sends seatControlConfigRequest messages."""
    print("Starting publisher test...")
    pm = messaging.PubMaster(['seatControlConfigRequest'])

    for i in range(5):
        print(f"Sending test message {i+1}...")

        # Create a test request message
        request = messaging.new_message('seatControlConfigRequest')
        request.seatControlConfigRequest.action = 0  # 'get' action
        request.seatControlConfigRequest.requestId = i + 1

        pm.send('seatControlConfigRequest', request)
        time.sleep(2)

    print("Publisher test complete")


def subscriber_test():
    """Test subscriber that listens for seatControlConfigRequest messages."""
    print("Starting subscriber test...")
    sm = messaging.SubMaster(['seatControlConfigRequest'])

    start_time = time.time()
    while time.time() - start_time < 12:  # Run for 12 seconds
        sm.update()

        if sm.updated['seatControlConfigRequest']:
            request = sm['seatControlConfigRequest']
            print(f"Received message! Type: {type(request)}")
            print(f"Message attributes: {dir(request)}")

            try:
                # Try direct access
                action = request.action
                request_id = request.requestId
                print(f"Direct access - Action: {action}, RequestId: {request_id}")
            except Exception as e:
                print(f"Direct access failed: {e}")

                try:
                    # Try nested access
                    action = request.seatControlConfigRequest.action
                    request_id = request.seatControlConfigRequest.requestId
                    print(f"Nested access - Action: {action}, RequestId: {request_id}")
                except Exception as e2:
                    print(f"Nested access failed: {e2}")

        time.sleep(0.1)

    print("Subscriber test complete")


def main():
    # Start subscriber in a separate thread
    subscriber_thread = threading.Thread(target=subscriber_test)
    subscriber_thread.start()

    # Wait a moment for subscriber to start
    time.sleep(1)

    # Start publisher
    publisher_test()

    # Wait for subscriber to finish
    subscriber_thread.join()


if __name__ == "__main__":
    main()
