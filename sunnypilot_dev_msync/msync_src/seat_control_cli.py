#!/usr/bin/env python3
"""Seat Control Hyperparameter CLI

Interactive & non-interactive CLI to inspect and modify seat control hyperparameters
without using the Qt UI. Updates the shared JSON config file that the running
seat_control_service_enhanced process polls for changes.

Usage Examples:
  # Show current config
  python -m sunnypilot_dev_msync.msync_src.seat_control_cli --show

  # Set individual parameters (non-interactive)
  python -m sunnypilot_dev_msync.msync_src.seat_control_cli --set frequency=30 turn_thresh_1=0.8 use_plan=true

  # Reset to defaults
  python -m sunnypilot_dev_msync.msync_src.seat_control_cli --reset

  # Launch interactive TUI style prompt loop
  python -m sunnypilot_dev_msync.msync_src.seat_control_cli --interactive
"""
from __future__ import annotations
import argparse
import sys
import time
from typing import Any  # Dict deprecated, use built-in generics

from sunnypilot_dev_msync.msync_src.parameter_manager import SeatControlParameterManager

PARAM_DISPLAY_ORDER = [
    'frequency', 'turn_thresh_1', 'turn_thresh_2', 'accel_thresh', 'decel_thresh',
    'long_smoothing', 'lat_smoothing', 'horizon', 'use_plan'
]

COLOR_OK = '\033[92m'
COLOR_ERR = '\033[91m'
COLOR_DIM = '\033[2m'
COLOR_RESET = '\033[0m'


def load_config(pm: SeatControlParameterManager) -> dict[str, Any]:
  return pm.get_current_config()


def print_config(config: dict[str, Any], header: str = "Current Seat Control Configuration"):
  print(f"\n{header}:")
  for k in PARAM_DISPLAY_ORDER:
    if k in config:
      print(f"  {k:16s}: {config[k]}")
  print()


def parse_set_args(pairs: list[str]) -> dict[str, Any]:
  parsed: dict[str, Any] = {}
  for item in pairs:
    if '=' not in item:
      raise ValueError(f"Invalid --set item '{item}', expected key=value")
    k, v = item.split('=', 1)
    k = k.strip()
    v = v.strip()
    if k == 'use_plan':
      v_conv: Any = v.lower() in ('1', 'true', 'yes', 'on')
    else:
      try:
        if k in ('frequency', 'long_smoothing', 'lat_smoothing'):
          v_conv = int(v)
        else:
          v_conv = float(v)
      except ValueError as exc:
        raise ValueError(f"Value for {k} must be numeric (got '{v}')") from exc
    parsed[k] = v_conv
  return parsed


def apply_updates(pm: SeatControlParameterManager, updates: dict[str, Any]) -> bool:
  current = pm.get_current_config()
  merged = current.copy()
  merged.update(updates)
  valid, err = pm.validate_config(merged)
  if not valid:
    print(f"{COLOR_ERR}Validation failed: {err}{COLOR_RESET}")
    return False
  ok, save_err = pm.set_config(merged)
  if not ok:
    print(f"{COLOR_ERR}Save failed: {save_err}{COLOR_RESET}")
    return False
  print(f"{COLOR_OK}Configuration updated successfully.{COLOR_RESET}")
  return True


def interactive_loop(pm: SeatControlParameterManager):
  print("Entering interactive mode. Type 'help' for commands, 'quit' to exit.")
  while True:
    try:
      config = pm.get_current_config()
      cmd = input().strip()  # removed prompt string for easier monkeypatch
      if not cmd:
        continue
      if cmd.lower() in ('quit', 'exit'):  # exit command
        break
      if cmd.lower() in ('show', 'print'):
        print_config(config)
        continue
      if cmd.lower() == 'help':
        print("""Commands:
  show / print          Display current configuration
  set key=value [...]    Update one or more parameters
  reset                  Reset to defaults
  watch [seconds]        Continuously print config on change (default 1s)
  quit / exit            Leave interactive mode
Parameters:
  frequency (int 1-100)
  turn_thresh_1 (float 0.1-10.0)
  turn_thresh_2 (float 0.1-15.0)
  accel_thresh (float 0.1-10.0)
  decel_thresh (float 0.1-10.0)
  long_smoothing (int 1-20)
  lat_smoothing (int 1-20)
  horizon (float 0.5-10.0)
  use_plan (bool true/false)
""")
        continue
      if cmd.lower().startswith('set '):
        parts = cmd.split()[1:]
        try:
          updates = parse_set_args(parts)
          apply_updates(pm, updates)
        except Exception as e:
          print(f"{COLOR_ERR}{e}{COLOR_RESET}")
        continue
      if cmd.lower().startswith('watch'):
        parts = cmd.split()
        interval = 1.0
        if len(parts) > 1:
          try:
            interval = float(parts[1])
          except ValueError:
            print(f"{COLOR_ERR}Invalid interval '{parts[1]}'{COLOR_RESET}")
            continue
        last_snapshot = None
        print(f"Watching config file every {interval}s. Ctrl-C to stop.")
        try:
          while True:
            snapshot = pm.get_current_config()
            if snapshot != last_snapshot:
              print_config(snapshot, header="(updated)")
              last_snapshot = snapshot.copy()
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Stopped watching.")
        continue
      if cmd.lower() == 'reset':
        pm.reset_to_defaults()
        print_config(pm.get_current_config(), header="Defaults Restored")
        continue
      print(f"{COLOR_ERR}Unknown command '{cmd}'. Type 'help'.{COLOR_RESET}")
    except (EOFError, KeyboardInterrupt):
      print()
      break


def main():
  parser = argparse.ArgumentParser(description="Seat Control Hyperparameter CLI")
  parser.add_argument('--show', action='store_true', help='Display current configuration and exit')
  parser.add_argument('--reset', action='store_true', help='Reset configuration to defaults')
  parser.add_argument('--set', nargs='*', default=[], metavar='key=value', help='Set one or more parameters')
  parser.add_argument('--interactive', action='store_true', help='Start interactive shell')
  args = parser.parse_args()

  pm = SeatControlParameterManager()  # messaging removed

  if args.reset:
    pm.reset_to_defaults()
    print_config(pm.get_current_config(), header="Defaults Restored")
    if not (args.show or args.set or args.interactive):
      return

  if args.set:
    try:
      updates = parse_set_args(args.set)
    except Exception as e:
      print(f"{COLOR_ERR}{e}{COLOR_RESET}")
      sys.exit(1)
    if not apply_updates(pm, updates):
      sys.exit(2)

  if args.show:
    print_config(pm.get_current_config())

  if args.interactive:
    interactive_loop(pm)

  if not (args.show or args.set or args.reset or args.interactive):
    # Default behavior: show config
    print_config(pm.get_current_config())


if __name__ == '__main__':
  main()
