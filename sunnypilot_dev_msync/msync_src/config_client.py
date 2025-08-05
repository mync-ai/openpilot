#!/usr/bin/env python3
"""
Seat Control Configuration Client

Simple client to test configuration changes with the enhanced seat control service.
"""

import sys
import time
import cereal.messaging as messaging


def send_config_request(action, config=None):
    """Send a configuration request to the seat control service."""
    pm = messaging.PubMaster(['seatControlConfigRequest'])
    sm = messaging.SubMaster(['seatControlConfig'])

    # Create request
    request = messaging.new_message('seatControlConfigRequest')
    request.seatControlConfigRequest.action = action
    request.seatControlConfigRequest.requestId = int(time.time() * 1000)  # Use timestamp as ID

    if config and action == 'set':
        request.seatControlConfigRequest.config.frequency = config['frequency']
        request.seatControlConfigRequest.config.turnThresh1 = config['turn_thresh_1']
        request.seatControlConfigRequest.config.turnThresh2 = config['turn_thresh_2']
        request.seatControlConfigRequest.config.longThresh = config['long_thresh']
        request.seatControlConfigRequest.config.smoothingWindow = config['smoothing_window']
        request.seatControlConfigRequest.config.horizon = config['horizon']
        request.seatControlConfigRequest.config.usePlan = config['use_plan']
        request.seatControlConfigRequest.config.timestamp = int(time.time() * 1e9)

    print(f"Sending {action} request...")
    pm.send('seatControlConfigRequest', request)

    # Wait for response
    print("Waiting for response...")
    start_time = time.time()
    timeout = 5.0  # 5 second timeout

    while time.time() - start_time < timeout:
        sm.update()
        if sm.updated['seatControlConfig']:
            response = sm['seatControlConfig']
            config_data = response.seatControlConfig

            received_config = {
                'frequency': config_data.frequency,
                'turn_thresh_1': config_data.turnThresh1,
                'turn_thresh_2': config_data.turnThresh2,
                'long_thresh': config_data.longThresh,
                'smoothing_window': config_data.smoothingWindow,
                'horizon': config_data.horizon,
                'use_plan': config_data.usePlan
            }

            print(f"Received response: {received_config}")
            return received_config

        time.sleep(0.05)

    print("No response received within timeout")
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python config_client.py get")
        print("  python config_client.py set --frequency 30 --turn-thresh-1 1.5")
        print("  python config_client.py reset")
        return

    action = sys.argv[1]

    if action == 'get':
        send_config_request('get')

    elif action == 'reset':
        send_config_request('reset')

    elif action == 'set':
        # Parse configuration arguments
        config = {
            'frequency': 20,
            'turn_thresh_1': 1.0,
            'turn_thresh_2': 2.5,
            'long_thresh': 1.0,
            'smoothing_window': 4,
            'horizon': 3.0,
            'use_plan': False
        }

        # Simple argument parsing
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == '--frequency' and i + 1 < len(args):
                config['frequency'] = int(args[i + 1])
                i += 2
            elif args[i] == '--turn-thresh-1' and i + 1 < len(args):
                config['turn_thresh_1'] = float(args[i + 1])
                i += 2
            elif args[i] == '--turn-thresh-2' and i + 1 < len(args):
                config['turn_thresh_2'] = float(args[i + 1])
                i += 2
            elif args[i] == '--long-thresh' and i + 1 < len(args):
                config['long_thresh'] = float(args[i + 1])
                i += 2
            elif args[i] == '--smoothing-window' and i + 1 < len(args):
                config['smoothing_window'] = int(args[i + 1])
                i += 2
            elif args[i] == '--horizon' and i + 1 < len(args):
                config['horizon'] = float(args[i + 1])
                i += 2
            elif args[i] == '--use-plan':
                config['use_plan'] = True
                i += 1
            else:
                i += 1

        print(f"Setting configuration: {config}")
        send_config_request('set', config)

    else:
        print(f"Unknown action: {action}")


if __name__ == "__main__":
    main()
