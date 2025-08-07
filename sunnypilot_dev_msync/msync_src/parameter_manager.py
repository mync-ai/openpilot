#!/usr/bin/env python3
"""
Seat Control Parameter Manager

This module manages the persistence and validation of seat control hyperparameters
using openpilot's Params system. It handles configuration requests from the UI
and publishes responses back.
"""

import sys
import os
import json
import time
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import cereal.messaging as messaging
from common.params import Params


class SeatControlParameterManager:
    """Manages seat control hyperparameters with validation and persistence."""

    # Default parameter values
    DEFAULT_CONFIG = {
        'frequency': 20,
        'turn_thresh_1': 1.0,
        'turn_thresh_2': 2.5,
        'long_thresh': 1.0,
        'smoothing_window': 4,
        'horizon': 3.0,
        'use_plan': False
    }

    # Parameter validation ranges
    PARAM_RANGES = {
        'frequency': (1, 100),
        'turn_thresh_1': (0.1, 10.0),
        'turn_thresh_2': (0.1, 15.0),
        'long_thresh': (0.1, 10.0),
        'smoothing_window': (1, 20),
        'horizon': (0.5, 10.0),
        'use_plan': (False, True)  # Boolean values
    }

    CURRENT_VERSION = 1

    def __init__(self):
        self.params = Params()
        self.pm = messaging.PubMaster(['seatControlConfig'])
        self.sm = messaging.SubMaster(['seatControlConfigRequest'])

        # Use a config file instead of individual params
        self.config_file = '/tmp/seat_control_config.json'

        # Initialize parameters if they don't exist
        self._initialize_default_params()

    def _initialize_default_params(self):
        """Initialize parameters with default values if they don't exist."""
        # Load existing config or create defaults
        config = self._load_config_from_file()
        if config is None:
            print(f"Initializing seat control parameters (version {self.CURRENT_VERSION})")
            self.reset_to_defaults()
        else:
            # Ensure all parameters exist
            for param_name, default_value in self.DEFAULT_CONFIG.items():
                if param_name not in config:
                    config[param_name] = default_value
                    print(f"Added missing parameter {param_name} with default: {default_value}")
            self._save_config_to_file(config)

    def _load_config_from_file(self) -> Optional[Dict[str, Any]]:
        """Load configuration from JSON file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
        return None

    def _save_config_to_file(self, config: Dict[str, Any]):
        """Save configuration to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config file: {e}")

    def _param_exists(self, param_name: str) -> bool:
        """Check if a parameter exists in the config file."""
        config = self._load_config_from_file()
        return config is not None and param_name in config

    def _set_param(self, param_name: str, value: Any):
        """Set a parameter in the config file."""
        config = self._load_config_from_file() or {}
        config[param_name] = value
        self._save_config_to_file(config)

    def _get_param(self, param_name: str) -> Any:
        """Get a parameter from the config file."""
        config = self._load_config_from_file()
        if config and param_name in config:
            return config[param_name]
        return self.DEFAULT_CONFIG[param_name]

    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate a configuration dictionary.

        Returns:
            tuple: (is_valid, error_message)
        """
        for param_name, value in config.items():
            if param_name not in self.PARAM_RANGES:
                return False, f"Unknown parameter: {param_name}"

            if param_name == 'use_plan':
                if not isinstance(value, bool):
                    return False, f"Parameter {param_name} must be boolean"
            elif param_name in ['frequency', 'smoothing_window']:
                if not isinstance(value, int):
                    return False, f"Parameter {param_name} must be integer"
                min_val, max_val = self.PARAM_RANGES[param_name]
                if not (min_val <= value <= max_val):
                    return False, f"Parameter {param_name} must be between {min_val} and {max_val}"
            else:  # float parameters
                if not isinstance(value, (int, float)):
                    return False, f"Parameter {param_name} must be numeric"
                min_val, max_val = self.PARAM_RANGES[param_name]
                if not (min_val <= value <= max_val):
                    return False, f"Parameter {param_name} must be between {min_val} and {max_val}"

        # Additional validation: turn_thresh_1 should be <= turn_thresh_2
        if 'turn_thresh_1' in config and 'turn_thresh_2' in config:
            if config['turn_thresh_1'] > config['turn_thresh_2']:
                return False, "turn_thresh_1 must be <= turn_thresh_2"

        return True, ""

    def get_current_config(self) -> Dict[str, Any]:
        """Load current configuration from config file."""
        config = self._load_config_from_file()
        if config:
            return config
        return self.DEFAULT_CONFIG.copy()

    def set_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Save configuration to config file with validation.

        Returns:
            tuple: (success, error_message)
        """
        # Validate configuration
        is_valid, error_msg = self.validate_config(config)
        if not is_valid:
            return False, error_msg

        # Save to config file
        try:
            self._save_config_to_file(config)
            print(f"Seat control configuration updated: {config}")
            return True, ""
        except Exception as e:
            return False, f"Failed to save configuration: {str(e)}"

    def reset_to_defaults(self):
        """Reset all parameters to default values."""
        self._save_config_to_file(self.DEFAULT_CONFIG.copy())
        print("Seat control parameters reset to defaults")

    def publish_config_response(self, config: Dict[str, Any], request_id: int = 0):
        """Publish current configuration to UI."""
        try:
            msg = messaging.new_message('seatControlConfig')
            msg.seatControlConfig.frequency = config['frequency']
            msg.seatControlConfig.turnThresh1 = config['turn_thresh_1']
            msg.seatControlConfig.turnThresh2 = config['turn_thresh_2']
            msg.seatControlConfig.longThresh = config['long_thresh']
            msg.seatControlConfig.smoothingWindow = config['smoothing_window']
            msg.seatControlConfig.horizon = config['horizon']
            msg.seatControlConfig.usePlan = config['use_plan']
            msg.seatControlConfig.timestamp = int(time.time() * 1e9)

            self.pm.send('seatControlConfig', msg)
        except Exception as e:
            print(f"Failed to publish config response: {e}")

    def handle_config_request(self):
        """Handle incoming configuration requests from UI."""
        if not self.sm.updated('seatControlConfigRequest'):
            return

        try:
            request = self.sm['seatControlConfigRequest']
            action = request.seatControlConfigRequest.action
            request_id = request.seatControlConfigRequest.requestId

            if action == 'get':
                # Send current configuration
                config = self.get_current_config()
                self.publish_config_response(config, request_id)

            elif action == 'set':
                # Set new configuration
                new_config = {
                    'frequency': request.seatControlConfigRequest.config.frequency,
                    'turn_thresh_1': request.seatControlConfigRequest.config.turnThresh1,
                    'turn_thresh_2': request.seatControlConfigRequest.config.turnThresh2,
                    'long_thresh': request.seatControlConfigRequest.config.longThresh,
                    'smoothing_window': request.seatControlConfigRequest.config.smoothingWindow,
                    'horizon': request.seatControlConfigRequest.config.horizon,
                    'use_plan': request.seatControlConfigRequest.config.usePlan
                }

                success, error_msg = self.set_config(new_config)
                if success:
                    # Send updated configuration back
                    self.publish_config_response(new_config, request_id)
                else:
                    print(f"Configuration update failed: {error_msg}")

            elif action == 'reset':
                # Reset to defaults
                self.reset_to_defaults()
                config = self.get_current_config()
                self.publish_config_response(config, request_id)

        except Exception as e:
            print(f"Error handling config request: {e}")

    def run_loop(self):
        """Main loop for handling configuration requests."""
        print("Seat Control Parameter Manager started")

        while True:
            try:
                self.sm.update()
                self.handle_config_request()
                time.sleep(0.05)  # 20Hz update rate
            except KeyboardInterrupt:
                print("Seat Control Parameter Manager stopping...")
                break
            except Exception as e:
                print(f"Error in parameter manager loop: {e}")
                time.sleep(1.0)  # Longer sleep on error


def test_parameter_manager():
    """Test the parameter manager functionality."""
    print("Testing Seat Control Parameter Manager...")

    manager = SeatControlParameterManager()

    # Test getting current config
    print("Current config:", manager.get_current_config())

    # Test setting a valid config
    test_config = {
        'frequency': 25,
        'turn_thresh_1': 1.5,
        'turn_thresh_2': 3.0,
        'long_thresh': 1.5,
        'smoothing_window': 5,
        'horizon': 2.5,
        'use_plan': True
    }

    success, error = manager.set_config(test_config)
    print(f"Set config result: {success}, error: {error}")

    if success:
        print("Updated config:", manager.get_current_config())

    # Test validation
    invalid_config = {'frequency': 200}  # Out of range
    success, error = manager.validate_config(invalid_config)
    print(f"Invalid config validation: {success}, error: {error}")

    # Test reset
    manager.reset_to_defaults()
    print("Config after reset:", manager.get_current_config())

    print("Parameter manager test completed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_parameter_manager()
    else:
        manager = SeatControlParameterManager()
        manager.run_loop()
