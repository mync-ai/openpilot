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

        print("DEBUG: Initializing messaging...")

        # Messaging for configuration requests
        try:
            self.config_pm = messaging.PubMaster(['seatControlConfig'])
            print("DEBUG: Created PubMaster for seatControlConfig")
        except Exception as e:
            print(f"DEBUG: Error creating PubMaster: {e}")

        try:
            self.config_sm = messaging.SubMaster(['seatControlConfigRequest'])
            print("DEBUG: Created SubMaster for seatControlConfigRequest")
        except Exception as e:
            print(f"DEBUG: Error creating SubMaster: {e}")

        # Main messaging for seat control
        self.topics = ['carState', 'carControl', 'modelV2', 'longitudinalPlan', 'radarState']
        self.sm = messaging.SubMaster(self.topics)

        # Load initial configuration
        if initial_config:
            # Use provided config (from command line)
            self.current_config = initial_config
            # Save to parameters for persistence
            success, error = self.parameter_manager.set_config(initial_config)
            if not success:
                print(f"Warning: Could not save initial config: {error}")
        else:
            # Load from stored parameters
            self.current_config = self.parameter_manager.get_current_config()

        print(f"Initialized with config: {self.current_config}")

        # Create initial components
        self._create_components()

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
        """Restart components with new configuration."""
        print("Restarting components with new configuration...")

        # Stop existing publisher
        if self.publisher:
            self.publisher.stop()

        # Create new components
        self._create_components()

        # Start new publisher if service is running
        if self.running and self.publisher:
            self.publisher.start()

        print("Components restarted successfully")

    def _handle_config_request(self):
        """Handle configuration requests from UI."""
        try:
            if not self.config_sm.updated['seatControlConfigRequest']:
                return

            request = self.config_sm['seatControlConfigRequest']

            # Debug: Print the message structure to understand how to access it
            print(f"DEBUG: Raw request message: {request}")
            print(f"DEBUG: Request type: {type(request)}")
            print(f"DEBUG: Request attributes: {dir(request)}")

            # Try different ways to access the data
            try:
                # Method 1: Direct access
                print(f"DEBUG: Trying direct access...")
                request_data = request

                # Convert enum to string or int properly
                action_enum = request_data.action
                print(f"DEBUG: Action enum: {action_enum}, type: {type(action_enum)}")

                # Convert enum to integer (Cap'n Proto enums have an ordinal value)
                if hasattr(action_enum, 'raw'):
                    action_value = action_enum.raw
                elif str(action_enum) in ['get', 'set', 'reset']:
                    action_names = ['get', 'set', 'reset']
                    action_value = action_names.index(str(action_enum))
                else:
                    # Try to extract the ordinal value
                    action_str = str(action_enum)
                    if action_str == 'get':
                        action_value = 0
                    elif action_str == 'set':
                        action_value = 1
                    elif action_str == 'reset':
                        action_value = 2
                    else:
                        action_value = 0  # default to get

                print(f"DEBUG: Direct access successful, action: {action_value}")
            except Exception as e1:
                print(f"DEBUG: Direct access failed: {e1}")
                try:
                    # Method 2: Through seatControlConfigRequest
                    print(f"DEBUG: Trying nested access...")
                    request_data = request.seatControlConfigRequest

                    action_enum = request_data.action
                    if hasattr(action_enum, 'raw'):
                        action_value = action_enum.raw
                    elif str(action_enum) in ['get', 'set', 'reset']:
                        action_names = ['get', 'set', 'reset']
                        action_value = action_names.index(str(action_enum))
                    else:
                        action_str = str(action_enum)
                        if action_str == 'get':
                            action_value = 0
                        elif action_str == 'set':
                            action_value = 1
                        elif action_str == 'reset':
                            action_value = 2
                        else:
                            action_value = 0

                    print(f"DEBUG: Nested access successful, action: {action_value}")
                except Exception as e2:
                    print(f"DEBUG: Nested access failed: {e2}")
                    return

            # Convert enum to string for comparison
            action_names = ['get', 'set', 'reset']  # Matching the capnp enum order
            action = action_names[action_value] if action_value < len(action_names) else 'unknown'

            print(f"Received config request: action={action}")

            if action == 'get':
                # Send current configuration
                self._publish_config_response(self.current_config, request_data.requestId)

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
                    self.current_config = new_config
                    self._restart_components()
                    self._publish_config_response(self.current_config, request_data.requestId)
                    print(f"Configuration updated: {self.current_config}")
                else:
                    print(f"Configuration validation failed: {error}")
                    # Send current config as response (indicating failure)
                    self._publish_config_response(self.current_config, request_data.requestId, error)

            elif action == 'reset':
                # Reset to defaults
                self.parameter_manager.reset_to_defaults()
                self.current_config = self.parameter_manager.get_current_config()
                self._restart_components()
                self._publish_config_response(self.current_config, request_data.requestId)
                print("Configuration reset to defaults")

        except Exception as e:
            print(f"Error handling config request: {e}")
            import traceback
            traceback.print_exc()

    def _publish_config_response(self, config, request_id, error_msg=None):
        """Publish configuration response."""
        try:
            response = messaging.new_message('seatControlConfig')
            response.seatControlConfig.frequency = config['frequency']
            response.seatControlConfig.turnThresh1 = config['turn_thresh_1']
            response.seatControlConfig.turnThresh2 = config['turn_thresh_2']
            response.seatControlConfig.longThresh = config['long_thresh']
            response.seatControlConfig.smoothingWindow = config['smoothing_window']
            response.seatControlConfig.horizon = config['horizon']
            response.seatControlConfig.usePlan = config['use_plan']
            response.seatControlConfig.timestamp = int(time.time() * 1e9)

            self.config_pm.send('seatControlConfig', response)

            if error_msg:
                print(f"Sent config response with error: {error_msg}")
            else:
                print(f"Sent config response: {config}")

        except Exception as e:
            print(f"Error publishing config response: {e}")
            import traceback
            traceback.print_exc()

    def start(self):
        """Start the seat control service."""
        if self.running:
            print("Service already running")
            return

        self.running = True

        try:
            print(f"Starting enhanced seat control service")
            print(f"Configuration: {self.current_config}")
            print(f"Subscribed topics: {', '.join(self.topics)}")

            # Start publisher
            if self.publisher:
                self.publisher.start()

            # Main service loop
            loop_count = 0
            while self.running:
                # Handle configuration requests
                self.config_sm.update()

                loop_count += 1
                if loop_count % 50 == 0:  # Print every 5 seconds (50 * 0.1s)
                    print(f"DEBUG: Service loop active, updated topics: {list(self.config_sm.updated.keys())}")
                    print(f"DEBUG: seatControlConfigRequest updated: {self.config_sm.updated.get('seatControlConfigRequest', False)}")

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
