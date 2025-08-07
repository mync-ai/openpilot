#!/usr/bin/env python3
"""
Enhanced Seat Control Service with Runtime Configuration

This service runs as a background process to publish seat control commands
to the messaging system for UI display. It supports runtime configuration
changes via the messaging system.
"""

import argparse
import sys
import os
import signal
import time
import threading
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

        # Initialize messaging attributes to None
        self.config_pm = None
        self.config_sm = None

        print("DEBUG: Initializing messaging...")

        # Configuration publishing (responses) - Should work based on test
        try:
            self.config_pm = messaging.PubMaster(['seatControlConfig'])
            print("DEBUG: Created PubMaster for seatControlConfig")
        except Exception as e:
            print(f"DEBUG: Error creating PubMaster for seatControlConfig: {e}")
            self.config_pm = None

        # Configuration subscribing (requests) - Should work based on test
        try:
            self.config_sm = messaging.SubMaster(['seatControlConfigRequest'])
            print("DEBUG: Created SubMaster for seatControlConfigRequest")
        except Exception as e:
            print(f"DEBUG: Error creating SubMaster for seatControlConfigRequest: {e}")
            self.config_sm = None

        # Main messaging for seat control
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

        print(f"Seat control configuration updated: {self.current_config}")
        print(f"Initialized with config: {self.current_config}")

        # Create components - this might be where the real issue is
        try:
            self._create_components()
            print("DEBUG: Components created successfully")
        except Exception as e:
            print(f"DEBUG: Error creating components: {e}")

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
                long_thresh=self.current_config['long_thresh'],
                smoothing_window=self.current_config['smoothing_window'],
                horizon=self.current_config['horizon'],
                use_plan=self.current_config['use_plan']
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

    def _handle_config_request(self):
        """Handle configuration requests from UI."""
        try:
            # Check if we can receive config requests
            if not self.config_sm:
                return

            if not self.config_sm.updated['seatControlConfigRequest']:
                return

            request = self.config_sm['seatControlConfigRequest']

            # Try to access the request data
            try:
                request_data = request
                action_enum = request_data.action

                # Convert enum to string
                action_str = str(action_enum)
                if action_str == 'get':
                    action_value = 0
                elif action_str == 'set':
                    action_value = 1
                elif action_str == 'reset':
                    action_value = 2
                else:
                    action_value = 0  # default to get

                action_names = ['get', 'set', 'reset']
                action = action_names[action_value] if action_value < len(action_names) else 'unknown'

                print(f"Received config request: action={action}")

                if action == 'get':
                    # Instead of publishing, write current config to a known location
                    # that the UI can read from
                    self._save_config_for_ui(self.current_config, request_data.requestId)

                elif action == 'set':
                    # Apply new configuration
                    new_config = {
                        'frequency': request_data.config.frequency,
                        'turn_thresh_1': request_data.config.turnThresh1,
                        'turn_thresh_2': request_data.config.turnThresh2,
                        'long_thresh': request_data.config.longThresh,
                        'smoothing_window': request_data.config.smoothingWindow,
                        'horizon': request_data.config.horizon,
                        'use_plan': request_data.config.usePlan
                    }

                    # Validate and save configuration
                    success, error = self.parameter_manager.set_config(new_config)

                    if success:
                        old_config = self.current_config.copy()
                        self.current_config = new_config

                        try:
                            self._restart_components()
                            self._save_config_for_ui(self.current_config, request_data.requestId)
                            print(f"Configuration updated successfully: {self.current_config}")
                        except Exception as restart_error:
                            print(f"Failed to restart components: {restart_error}")
                            # Revert to old configuration
                            self.current_config = old_config
                            print("Reverted to previous configuration")
                            self._save_config_for_ui(self.current_config, request_data.requestId,
                                                   f"Configuration update failed: {str(restart_error)}")
                    else:
                        print(f"Configuration validation failed: {error}")
                        self._save_config_for_ui(self.current_config, request_data.requestId, error)

                elif action == 'reset':
                    # Reset to defaults
                    self.parameter_manager.reset_to_defaults()
                    self.current_config = self.parameter_manager.get_current_config()
                    self._restart_components()
                    self._save_config_for_ui(self.current_config, request_data.requestId)
                    print("Configuration reset to defaults")

            except Exception as e:
                print(f"Error processing config request: {e}")

        except Exception as e:
            print(f"Error handling config request: {e}")
            import traceback
            traceback.print_exc()

    def _save_config_for_ui(self, config, request_id, error_msg=None):
        """Save configuration response to a file that the UI can read."""
        try:
            import json

            response_data = {
                'requestId': request_id,
                'timestamp': int(time.time() * 1e9),
                'config': config,
                'error': error_msg,
                'success': error_msg is None
            }

            # Save to a temporary file that the UI can poll
            response_file = '/tmp/seat_control_config_response.json'
            with open(response_file, 'w') as f:
                json.dump(response_data, f, indent=2)

            print(f"Saved config response to {response_file}")

            if error_msg:
                print(f"Config response with error: {error_msg}")
            else:
                print(f"Config response saved: {config}")

        except Exception as e:
            print(f"Error saving config response: {e}")

    def start(self):
        """Start the seat control service."""
        if self.running:
            print("Service already running")
            return

        self.running = True

        try:
            print("Starting enhanced seat control service")
            print(f"Configuration: {self.current_config}")
            print(f"Subscribed topics: {', '.join(self.topics)}")

            # Check messaging status
            if self.config_pm:
                print("DEBUG: Configuration publisher available - can respond to UI requests")
            else:
                print("DEBUG: Configuration publisher unavailable - running in read-only mode")

            if self.config_sm:
                print("DEBUG: Configuration subscriber available - can receive UI requests")
            else:
                print("DEBUG: Cannot receive configuration requests")

            # Start publisher
            if self.publisher:
                self.publisher.start()
                print("DEBUG: Seat control publisher started")

            # Main service loop
            while self.running:
                # Handle configuration requests (only if we have a subscriber)
                if self.config_sm:
                    self.config_sm.update()

                    # Debug: Check if we have any messages
                    if 'seatControlConfigRequest' in self.config_sm.updated:
                        if self.config_sm.updated['seatControlConfigRequest']:
                            print("DEBUG: Received config request message")

                    self._handle_config_request()

                # Small sleep to prevent excessive CPU usage
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
    parser = argparse.ArgumentParser(description='Enhanced Seat Control Service with Runtime Configuration')
    parser.add_argument('--frequency', type=int, default=20, help='Update frequency in Hz')
    parser.add_argument('--turn-thresh-1', type=float, default=1.0, help='First turn threshold')
    parser.add_argument('--turn-thresh-2', type=float, default=2.5, help='Second turn threshold')
    parser.add_argument('--long-thresh', type=float, default=1.0, help='Longitudinal threshold')
    parser.add_argument('--horizon', type=float, default=3.0, help='Time horizon for predictions in seconds')
    parser.add_argument('--smoothing-window', type=int, default=4, help='Smoothing window size')
    parser.add_argument('--use-plan', action='store_true', default=False,
                       help='Use plan data instead of prediction data for longitudinal decisions')
    parser.add_argument('--use-stored-config', action='store_true', default=False,
                       help='Use stored configuration instead of command line arguments')

    args = parser.parse_args()

    if args.use_stored_config:
        # Load configuration from stored parameters
        service = EnhancedSeatControlService()
    else:
        # Use command line configuration
        config = {
            'frequency': args.frequency,
            'turn_thresh_1': args.turn_thresh_1,
            'turn_thresh_2': args.turn_thresh_2,
            'long_thresh': args.long_thresh,
            'smoothing_window': args.smoothing_window,
            'horizon': args.horizon,
            'use_plan': args.use_plan
        }
        service = EnhancedSeatControlService(initial_config=config)

    service.start()


if __name__ == "__main__":
    main()
