#!/usr/bin/env python3
"""
Simple test to verify messaging between seat control service and client.
"""

import sys
import os
import time
import threading

# Add the openpilot root to the path
# When running from sunnypilot_dev_msync/tests/, we need to go up two levels to reach openpilot root
current_dir = os.path.dirname(os.path.abspath(__file__))
openpilot_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, openpilot_root)

import cereal.messaging as messaging


def test_basic_messaging():
    """Test basic messaging between publisher and subscriber."""
    print("=== Testing Basic Messaging ===")

    # Test 1: Basic message creation
    try:
        print("Creating test messages...")
        config_request = messaging.new_message('seatControlConfigRequest')
        config_response = messaging.new_message('seatControlConfig')
        print("✅ Message creation successful")
    except Exception as e:
        print(f"❌ Message creation failed: {e}")
        return False

    # Test 2: Publisher/Subscriber creation
    try:
        print("Creating PubMaster and SubMaster...")
        pm = messaging.PubMaster(['seatControlConfigRequest', 'seatControlConfig'])
        sm = messaging.SubMaster(['seatControlConfigRequest', 'seatControlConfig'])
        print("✅ PubMaster/SubMaster creation successful")
    except Exception as e:
        print(f"❌ PubMaster/SubMaster creation failed: {e}")
        return False

    # Test 3: Simple message send/receive
    try:
        print("Testing message send/receive...")

        # Create a simple config request
        print("Creating request message...")
        request = messaging.new_message('seatControlConfigRequest')

        print("Setting action field...")
        request.seatControlConfigRequest.action = 0  # 'get' enum value

        print("Setting requestId field...")
        request.seatControlConfigRequest.requestId = 12345

        print("Sending test message...")
        pm.send('seatControlConfigRequest', request)

        # Try to receive it
        print("Waiting for message...")
        for i in range(50):  # Wait up to 5 seconds
            sm.update()
            if sm.updated['seatControlConfigRequest']:
                received = sm['seatControlConfigRequest']
                request_id = received.requestId
                if request_id == 12345:
                    print("✅ Message send/receive successful")
                    return True
            time.sleep(0.1)

        print("❌ No message received within timeout")
        return False

    except Exception as e:
        print(f"❌ Message send/receive failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_communication():
    """Test communication with the actual service."""
    print("\n=== Testing Service Communication ===")

    # Start a minimal config responder
    def config_responder():
        try:
            pm = messaging.PubMaster(['seatControlConfig'])
            sm = messaging.SubMaster(['seatControlConfigRequest'])

            print("Config responder started...")

            for i in range(100):  # Run for 10 seconds
                sm.update()
                if sm.updated['seatControlConfigRequest']:
                    print(f"Responder received request!")
                    request = sm['seatControlConfigRequest']

                    # Access request data directly (not nested)
                    print(f"Request action: {request.action}, requestId: {request.requestId}")

                    # Send a simple response
                    response = messaging.new_message('seatControlConfig')
                    response.seatControlConfig.frequency = 20
                    response.seatControlConfig.turnThresh1 = 1.0
                    response.seatControlConfig.turnThresh2 = 2.5
                    response.seatControlConfig.longThresh = 1.0
                    response.seatControlConfig.smoothingWindow = 4
                    response.seatControlConfig.horizon = 3.0
                    response.seatControlConfig.usePlan = False
                    response.seatControlConfig.timestamp = int(time.time() * 1e9)

                    pm.send('seatControlConfig', response)
                    print("Responder sent response!")
                    return  # Exit after sending one response

                time.sleep(0.05)

        except Exception as e:
            print(f"Responder error: {e}")
            import traceback
            traceback.print_exc()

    # Start responder in background
    responder_thread = threading.Thread(target=config_responder, daemon=True)
    responder_thread.start()

    time.sleep(0.2)  # Give responder time to start

    # Test client
    try:
        print("Testing client...")
        pm = messaging.PubMaster(['seatControlConfigRequest'])
        sm = messaging.SubMaster(['seatControlConfig'])

        # Give SubMaster time to initialize
        time.sleep(0.1)

        # Send request
        request = messaging.new_message('seatControlConfigRequest')
        request.seatControlConfigRequest.action = 0  # 'get' enum value
        request.seatControlConfigRequest.requestId = 54321

        print("Client sending request...")
        pm.send('seatControlConfigRequest', request)

        # Wait for response
        for i in range(100):  # Wait longer - 10 seconds
            sm.update()
            if sm.updated['seatControlConfig']:
                response = sm['seatControlConfig']
                # Access response data directly (not nested)
                print(f"✅ Client received response: frequency={response.frequency}")
                return True
            time.sleep(0.1)

        print("❌ Client did not receive response")

        # Wait for responder thread to finish
        responder_thread.join(timeout=1.0)
        return False

    except Exception as e:
        print(f"❌ Client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing Seat Control Messaging System")

    # Test basic messaging
    basic_success = test_basic_messaging()

    # Test service communication
    service_success = test_service_communication()

    print(f"\n=== Results ===")
    print(f"Basic messaging: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"Service communication: {'✅ PASS' if service_success else '❌ FAIL'}")

    if basic_success and service_success:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed - check messaging configuration")
