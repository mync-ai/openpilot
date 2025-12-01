#!/usr/bin/env python3
"""Seat Control Parameter Manager (file-based only, messaging removed)

Provides validation, defaults, persistence to a JSON file. Former messaging
paths (Pub/Sub, request handling loops) have been removed in favor of the
simpler file hot-reload mechanism used by the service & CLI.
"""

from __future__ import annotations
import os
import json
from typing import Any


class SeatControlParameterManager:
    DEFAULT_CONFIG: dict[str, Any] = {
        'frequency': 20,
        'turn_thresh_1': 0.75,
        'turn_thresh_2': 2.25,
        'accel_thresh_1': 1.75,
        'accel_thresh_2': 1.75,
        'decel_thresh_1': 1.0,
        'decel_thresh_2': 1.5,
        'long_sens': 10,
        'lat_sens': 8,
        'long_sticky': 10,
        'lat_sticky': 5,
        'long_horizon': 3.0,
        'lat_horizon': 4.0,
        'use_plan': False,
        'lockout_speed': 3.0,
        'long_horizon_offset': 1.0,
        'lat_horizon_offset': 1.5,
    }

    PARAM_RANGES: dict[str, tuple[Any, Any]] = {
        'frequency': (1, 100),
        'turn_thresh_1': (0.1, 10.0),
        'turn_thresh_2': (0.1, 15.0),
        'accel_thresh_1': (0.1, 10.0),
        'accel_thresh_2': (0.1, 15.0),
        'decel_thresh_1': (0.1, 10.0),
        'decel_thresh_2': (0.1, 15.0),
        'long_sens': (1, 20),
        'lat_sens': (1, 20),
        'long_sticky': (1, 20),
        'lat_sticky': (1, 20),
        'long_horizon': (0.5, 10.0),
        'lat_horizon': (0.5, 10.0),
        'use_plan': (False, True),
        'lockout_speed': (0.0, 20.0),
        'long_horizon_offset': (0.0, 9.0),
        'lat_horizon_offset': (0.0, 9.0),
    }

    CURRENT_VERSION = 1

    def __init__(self, config_file: str | None = None):
        self.config_file = config_file or '/tmp/seat_control_config.json'
        self._initialize_default_params()

    def _initialize_default_params(self):
        cfg = self._load_config_from_file()
        if cfg is None:
            self.reset_to_defaults()
        else:
            changed = False
            for k, v in self.DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
                    changed = True
            if changed:
                self._save_config_to_file(cfg)

    def _load_config_from_file(self) -> dict[str, Any] | None:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file) as f:
                    return json.load(f)
        except Exception as e:  # pragma: no cover
            print(f"Error loading config file: {e}")
        return None

    def _save_config_to_file(self, config: dict[str, Any]):
        try:
            tmp_path = self.config_file + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(config, f, indent=2)
            os.replace(tmp_path, self.config_file)
        except Exception as e:  # pragma: no cover
            print(f"Error saving config file: {e}")

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
        for name, value in config.items():
            if name not in self.PARAM_RANGES:
                return False, f"Unknown parameter: {name}"
            if name == 'use_plan':
                if not isinstance(value, bool):
                    return False, f"Parameter {name} must be boolean"
            elif name in ('frequency', 'long_sens', 'lat_sens', 'long_sticky', 'lat_sticky'):
                if not isinstance(value, int):
                    return False, f"Parameter {name} must be integer"
                lo, hi = self.PARAM_RANGES[name]
                if not (lo <= value <= hi):
                    return False, f"Parameter {name} must be between {lo} and {hi}"
            else:
                if not isinstance(value, (int, float)):
                    return False, f"Parameter {name} must be numeric"
                lo, hi = self.PARAM_RANGES[name]
                if not (lo <= float(value) <= hi):
                    return False, f"Parameter {name} must be between {lo} and {hi}"
        if 'turn_thresh_1' in config and 'turn_thresh_2' in config and config['turn_thresh_1'] > config['turn_thresh_2']:
            return False, 'turn_thresh_1 must be <= turn_thresh_2'
        if 'accel_thresh_1' in config and 'accel_thresh_2' in config and config['accel_thresh_1'] > config['accel_thresh_2']:
            return False, 'accel_thresh_1 must be <= accel_thresh_2'
        if 'decel_thresh_1' in config and 'decel_thresh_2' in config and config['decel_thresh_1'] > config['decel_thresh_2']:
            return False, 'decel_thresh_1 must be <= decel_thresh_2'
        return True, ''

    def get_current_config(self) -> dict[str, Any]:
        return self._load_config_from_file() or self.DEFAULT_CONFIG.copy()

    def set_config(self, config: dict[str, Any]) -> tuple[bool, str]:
        valid, err = self.validate_config(config)
        if not valid:
            return False, err
        self._save_config_to_file(config)
        print(f"Seat control configuration updated: {config}")
        return True, ''

    def reset_to_defaults(self):
        self._save_config_to_file(self.DEFAULT_CONFIG.copy())
        print("Seat control parameters reset to defaults")

    def touch_timestamp(self):
        try:
            os.utime(self.config_file, None)
        except OSError:
            pass


orig_init = SeatControlParameterManager.__init__

def _shimmed_init(self, *args, **kwargs):  # type: ignore
    if 'enable_messaging' in kwargs:
        kwargs.pop('enable_messaging')
    return orig_init(self, *args, **kwargs)
SeatControlParameterManager.__init__ = _shimmed_init  # type: ignore
