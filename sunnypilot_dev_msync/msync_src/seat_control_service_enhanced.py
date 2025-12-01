#!/usr/bin/env python3
"""Enhanced Seat Control Service (file-based config only)

Messaging-based configuration request/response paths removed. Configuration
changes are applied by editing the JSON file watched by this process.
"""

import argparse
import sys
import os
import signal
import time
import cereal.messaging as messaging

from sunnypilot_dev_msync.msync_src import short_control
from sunnypilot_dev_msync.msync_src.seat_control_integration import SeatControlPublisher
from sunnypilot_dev_msync.msync_src.parameter_manager import SeatControlParameterManager


class EnhancedSeatControlService:
    """Enhanced seat control service with runtime configuration support."""

    def __init__(self, initial_config=None):
        self.running = False
        self.decider = None
        self.publisher = None
        self.parameter_manager = SeatControlParameterManager()

        # Only subscribe to data topics needed for decisions
        self.topics = ['carState', 'carControl', 'modelV2', 'longitudinalPlan', 'radarState']
        self.sm = messaging.SubMaster(self.topics)

        # Load initial configuration
        if initial_config:
            self.current_config = initial_config
            success, error = self.parameter_manager.set_config(initial_config)
            if not success:
                print(f"Warning: Could not save initial config: {error}")
        else:
            self.current_config = self.parameter_manager.get_current_config()

        print(f"Initialized with config: {self.current_config}")

        # Track config file for external (CLI) edits (no re-import needed)
        self._config_file_path = getattr(self.parameter_manager, 'config_file', '/tmp/seat_control_config.json')
        if os.path.exists(self._config_file_path):
            self._last_config_mtime = os.path.getmtime(self._config_file_path)
        else:
            self._last_config_mtime = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("Received shutdown signal, stopping seat control service...")
        self.stop()
        sys.exit(0)

    def _create_components(self):
        """Create decider and publisher with current configuration."""
        try:
            # Create decider with current config
            self.decider = short_control.Decider(
                turn_thresh_1=self.current_config['turn_thresh_1'],
                turn_thresh_2=self.current_config['turn_thresh_2'],
                accel_thresh_1=self.current_config['accel_thresh_1'],
                accel_thresh_2=self.current_config['accel_thresh_2'],
                decel_thresh_1=self.current_config['decel_thresh_1'],
                decel_thresh_2=self.current_config['decel_thresh_2'],
                long_sens=self.current_config['long_sens'],
                lat_sens=self.current_config['lat_sens'],
                long_sticky=self.current_config['long_sticky'],
                lat_sticky=self.current_config['lat_sticky'],
                long_horizon=self.current_config['long_horizon'],
                long_horizon_offset=self.current_config['long_horizon_offset'],
                lat_horizon=self.current_config['lat_horizon'],
                lat_horizon_offset=self.current_config['lat_horizon_offset'],
                use_plan=self.current_config['use_plan'],
                lockout_speed=self.current_config.get('lockout_speed', 2.5)
            )

            # Create publisher with current config
            self.publisher = SeatControlPublisher(
                self.decider,
                self.sm,
                update_frequency=self.current_config['frequency']
            )

            print(f"Components created with config: {self.current_config}")

        except Exception as e:
            print(f"Error creating components: {e}")
            raise

    def _restart_components(self):
        """Restart all components with proper cleanup"""
        import time

        try:
            print("Restarting components with new configuration...")

            # Stop current publisher
            if self.publisher:
                print("Stopping current publisher...")
                self.publisher.stop()
                self.publisher = None
                time.sleep(0.5)  # Allow time for cleanup

            # Recreate components with new configuration
            self._create_components()

            # Restart publisher
            if self.publisher:
                print("Starting new publisher...")
                self.publisher.start()

            print("Component restart completed successfully")

        except Exception as e:
            print(f"Error during component restart: {e}")
            raise

    def _reload_config_from_file(self):
        """Reload configuration directly from JSON file and restart components if changed."""
        try:
            import json
            if not os.path.exists(self._config_file_path):
                return
            with open(self._config_file_path) as f:  # mode argument optional
                new_config = json.load(f)
        except Exception as e:
            print(f"Config reload failed: {e}")
            return
        # Validate using parameter manager to ensure consistency
        valid, err = self.parameter_manager.validate_config(new_config)
        if not valid:
            print(f"Ignored invalid external config edit: {err}")
            return
        if new_config != self.current_config:
            print(f"Detected external config change: {new_config}")
            old_config = self.current_config.copy()
            self.current_config = new_config
            try:
                self._restart_components()
            except Exception as e:
                print(f"Failed to apply external config change, reverting: {e}")
                self.current_config = old_config

    def _poll_config_file(self):
        """Check JSON file mtime for external changes (CLI edits)."""
        try:
            if not self._config_file_path:
                return
            if os.path.exists(self._config_file_path):
                mtime = os.path.getmtime(self._config_file_path)
                if mtime > self._last_config_mtime:
                    self._last_config_mtime = mtime
                    self._reload_config_from_file()
        except Exception as e:
            print(f"Config file poll error: {e}")

    def start(self):
        """Start the seat control service."""
        if self.running:
            print("Service already running")
            return

        self.running = True

        # Ensure components are created before starting publisher/main loop
        self._create_components()

        try:
            print("Starting enhanced seat control service (file-based config)")
            print(f"Configuration: {self.current_config}")
            print(f"Subscribed topics: {', '.join(self.topics)}")

            # Start publisher
            if self.publisher:
                self.publisher.start()
                print("DEBUG: Seat control publisher started")

            # Main service loop
            while self.running:
                # File-based config polling (preferred over messaging now)
                self._poll_config_file()
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("Shutting down seat control service...")
            self.stop()
        except Exception as e:
            print(f"Error in seat control service: {e}")
            self.stop()
            raise

    def stop(self):
        """Stop the seat control service."""
        if not self.running:
            return

        print("Stopping seat control service...")
        self.running = False

        if self.publisher:
            self.publisher.stop()

        print("Seat control service stopped")


def run_service_enhanced(**kwargs):
    """Run the enhanced seat control service with given configuration."""
    service = EnhancedSeatControlService(initial_config=kwargs)
    service.start()


def main():
    parser = argparse.ArgumentParser(description='Enhanced Seat Control Service (file-based config)')
    parser.add_argument('--frequency', type=int, default=20, help='Update frequency in Hz')
    parser.add_argument('--turn-thresh-1', type=float, default=0.75, help='First turn threshold')
    parser.add_argument('--turn-thresh-2', type=float, default=2.25, help='Second turn threshold')
    parser.add_argument('--accel-thresh-1', type=float, default=1.75, help='First acceleration threshold')
    parser.add_argument('--accel-thresh-2', type=float, default=1.75, help='Second acceleration threshold')
    parser.add_argument('--decel-thresh-1', type=float, default=1.0, help='First deceleration threshold')
    parser.add_argument('--decel-thresh-2', type=float, default=1.5, help='Second deceleration threshold')
    parser.add_argument('--long-sens', type=int, default=10, help='Longitudinal sensitivity window')
    parser.add_argument('--lat-sens', type=int, default=8, help='Lateral sensitivity window')
    parser.add_argument('--long-sticky', type=int, default=10, help='Longitudinal sticky window')
    parser.add_argument('--lat-sticky', type=int, default=5, help='Lateral sticky window')
    parser.add_argument('--long-horizon', type=float, default=3.0,
                        help='Override time horizon for longitudinal decisions (defaults to --horizon)')
    parser.add_argument('--long-horizon-offset', type=float, default=1.0,
                        help='Override horizon offset for longitudinal decisions (defaults to --horizon-offset)')
    parser.add_argument('--lat-horizon', type=float, default=4.0,
                        help='Override time horizon for lateral decisions (defaults to --horizon)')
    parser.add_argument('--lat-horizon-offset', type=float, default=1.5,
                        help='Override horizon offset for lateral decisions (defaults to --horizon-offset)')
    parser.add_argument('--use-plan', action='store_true', default=False,
                       help='Use plan data instead of prediction data for longitudinal decisions')
    parser.add_argument('--lockout-speed', type=float, default=3.0, help='Lockout speed for roll lockout')

    args = parser.parse_args()

    # Use command line configuration
    config = {
        'frequency': args.frequency,
        'turn_thresh_1': args.turn_thresh_1,
        'turn_thresh_2': args.turn_thresh_2,
        'accel_thresh_1': args.accel_thresh_1,
        'accel_thresh_2': args.accel_thresh_2,
        'decel_thresh_1': args.decel_thresh_1,
        'decel_thresh_2': args.decel_thresh_2,
        'long_sens': args.long_sens,
        'lat_sens': args.lat_sens,
        'long_sticky': args.long_sticky,
        'lat_sticky': args.lat_sticky,
        'long_horizon': args.long_horizon,
        'long_horizon_offset': args.long_horizon_offset,
        'lat_horizon': args.lat_horizon,
        'lat_horizon_offset': args.lat_horizon_offset,
        'use_plan': args.use_plan,
        'lockout_speed': args.lockout_speed
    }
    service = EnhancedSeatControlService(initial_config=config)

    service.start()


if __name__ == "__main__":
    main()
