#!/usr/bin/env python3
import os
import json
import pytest

from sunnypilot_dev_msync.msync_src.parameter_manager import SeatControlParameterManager
from sunnypilot_dev_msync.msync_src import seat_control_cli as cli


class TempConfigPM(SeatControlParameterManager):
  def __init__(self, tmp_path):
    super().__init__(enable_messaging=False)  # disable messaging for isolated tests
    # Override config file location to isolate tests
    self.config_file = os.path.join(tmp_path, 'seat_control_config.json')
    # Initialize file with defaults
    self.reset_to_defaults()


@pytest.fixture()
def pm(tmp_path):
  return TempConfigPM(str(tmp_path))


def read_json(pm: TempConfigPM):
  with open(pm.config_file) as f:
    return json.load(f)


def test_parse_set_args():
  result = cli.parse_set_args(["frequency=30", "turn_thresh_1=0.8", "use_plan=true"])
  assert result['frequency'] == 30
  assert abs(result['turn_thresh_1'] - 0.8) < 1e-6
  assert result['use_plan'] is True


def test_apply_updates_valid(pm):
  ok = cli.apply_updates(pm, {"frequency": 25, "horizon": 4.0})
  assert ok
  cfg = read_json(pm)
  assert cfg['frequency'] == 25
  assert abs(cfg['horizon'] - 4.0) < 1e-6


def test_apply_updates_invalid(pm):
  ok = cli.apply_updates(pm, {"frequency": 1000})  # out of range
  assert not ok
  cfg = read_json(pm)
  assert cfg['frequency'] != 1000


def test_interactive_set_command(pm, monkeypatch):
  # Simulate a short interactive session: set + show + quit
  inputs = iter([
    "set frequency=35 smoothing_window=6",
    "show",
    "quit"
  ])
  monkeypatch.setattr('builtins.input', lambda: next(inputs))
  cli.interactive_loop(pm)
  cfg = read_json(pm)
  assert cfg['frequency'] == 35
  assert cfg['smoothing_window'] == 6


def test_reset(pm):
  cli.apply_updates(pm, {"frequency": 33})
  pm.reset_to_defaults()
  cfg = read_json(pm)
  assert cfg['frequency'] == pm.DEFAULT_CONFIG['frequency']
