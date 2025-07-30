#!/usr/bin/env python3
"""
Seat Control Service

This service runs as a background process to publish seat control commands
to the messaging system for UI display.
"""

import argparse
import sys
import os
import signal
import time
import cereal.messaging as messaging

from sunnypilot_dev_msync.msync_src import short_control
from sunnypilot_dev_msync.msync_src.seat_control_integration import SeatControlPublisher


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("Received shutdown signal, stopping seat control service...")
    global publisher
    if publisher:
        publisher.stop()
    sys.exit(0)


def run_service(frequency=20, turn_thresh_1=1.0, turn_thresh_2=2.5, long_thresh=1.0, smoothing_window=4,
                horizon=3.0, use_plan=False, topics=['carState', 'carControl', 'modelV2', 'longitudinalPlan', 'radarState']):
    global publisher

    # Create SubMaster with specified topics
    sm = messaging.SubMaster(topics)

    decider = short_control.Decider(
        turn_thresh_1=turn_thresh_1,
        turn_thresh_2=turn_thresh_2,
        long_thresh=long_thresh,
        smoothing_window=smoothing_window,
        horizon=horizon,
        use_plan=use_plan
    )
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    publisher = SeatControlPublisher(decider, sm, update_frequency=frequency)
    try:
        print(f"Starting seat control service at {frequency} Hz")
        print(f"Subscribed topics: {', '.join(topics)}")
        publisher.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down seat control service...")
        publisher.stop()
        sys.exit(0)
    except Exception as e:
        print(f"Error in seat control service: {e}")
        publisher.stop()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Seat Control Service')
    parser.add_argument('--frequency', type=int, default=20, help='Update frequency in Hz')
    parser.add_argument('--turn-thresh-1', type=float, default=1.0, help='First turn threshold')
    parser.add_argument('--turn-thresh-2', type=float, default=2.5, help='Second turn threshold')
    parser.add_argument('--long-thresh', type=float, default=1.0, help='Longitudinal threshold')
    parser.add_argument('--horizon', type=float, default=2.5, help='Horizon for planning/prediction')
    parser.add_argument('--smoothing-window', type=int, default=4, help='Smoothing window size')
    parser.add_argument('--use-plan', action='store_true', default=False,
                       help='Use plan data instead of prediction data for longitudinal decisions')
    parser.add_argument('--topics', nargs='+',
                       default=['carState', 'carControl', 'modelV2', 'longitudinalPlan', 'radarState'],
                       help='List of topics to subscribe to')
    args = parser.parse_args()
    run_service(
        frequency=args.frequency,
        turn_thresh_1=args.turn_thresh_1,
        turn_thresh_2=args.turn_thresh_2,
        long_thresh=args.long_thresh,
        smoothing_window=args.smoothing_window,
        horizon=args.horizon,
        use_plan=args.use_plan,
        topics=args.topics
    )


if __name__ == "__main__":
    main()
