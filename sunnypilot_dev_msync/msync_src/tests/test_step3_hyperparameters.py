#!/usr/bin/env python3
"""Test CLI interactive mode with new hyperparameters."""

import sys
import io
from contextlib import redirect_stdout, redirect_stdin

# Add project to path
sys.path.insert(0, '/home/kerrb/msync_branching/openpilot')

from sunnypilot_dev_msync.msync_src.seat_control_cli import interactive_loop, parse_set_args
from sunnypilot_dev_msync.msync_src.parameter_manager import SeatControlParameterManager


def test_cli_interactive_commands():
    """Test CLI interactive commands handle new parameters correctly."""
    pm = SeatControlParameterManager()

    # Test parameter parsing
    test_cases = [
        "accel_thresh=2.5 decel_thresh=1.8",
        "long_smoothing=6 lat_smoothing=4",
        "frequency=25 horizon=4.0",
        "use_plan=true"
    ]

    for case in test_cases:
        try:
            parsed = parse_set_args(case.split())
            print(f"✓ Parsed '{case}': {parsed}")
        except Exception as e:
            print(f"✗ Failed to parse '{case}': {e}")
            return False

    # Test validation
    test_config = {
        'frequency': 25,
        'turn_thresh_1': 1.0,
        'turn_thresh_2': 2.5,
        'accel_thresh': 2.5,
        'decel_thresh': 1.8,
        'long_smoothing': 6,
        'lat_smoothing': 4,
        'horizon': 4.0,
        'use_plan': True
    }

    valid, error = pm.validate_config(test_config)
    if not valid:
        print(f"✗ Config validation failed: {error}")
        return False

    print(f"✓ Config validation passed: {test_config}")
    return True


def test_parameter_ranges():
    """Test parameter range validation for new parameters."""
    pm = SeatControlParameterManager()

    test_cases = [
        # Valid cases
        ({'accel_thresh': 2.0}, True),
        ({'decel_thresh': 1.5}, True),
        ({'long_smoothing': 5}, True),
        ({'lat_smoothing': 3}, True),

        # Invalid cases - out of range
        ({'accel_thresh': 0.05}, False),  # Below minimum
        ({'decel_thresh': 15.0}, False),  # Above maximum
        ({'long_smoothing': 0}, False),   # Below minimum
        ({'lat_smoothing': 25}, False),   # Above maximum

        # Invalid cases - wrong type
        ({'long_smoothing': 3.5}, False),  # Should be int
        ({'lat_smoothing': 'invalid'}, False),  # Should be int
    ]

    base_config = pm.get_current_config()

    for updates, should_be_valid in test_cases:
        test_config = base_config.copy()
        test_config.update(updates)

        valid, error = pm.validate_config(test_config)
        if valid != should_be_valid:
            print(f"✗ Validation mismatch for {updates}: expected {should_be_valid}, got {valid} ({error})")
            return False

        if should_be_valid:
            print(f"✓ Valid: {updates}")
        else:
            print(f"✓ Invalid (expected): {updates} - {error}")

    return True


def test_cli_help_content():
    """Test that CLI help includes all new parameters."""
    # Capture help output
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()

    try:
        from sunnypilot_dev_msync.msync_src.seat_control_cli import main
        sys.argv = ['seat_control_cli.py', '--help']
        try:
            main()
        except SystemExit:
            pass  # argparse calls sys.exit after showing help
    finally:
        sys.stdout = old_stdout

    help_text = captured_output.getvalue()

    required_params = [
        'accel_thresh', 'decel_thresh',
        'long_smoothing', 'lat_smoothing'
    ]

    for param in required_params:
        if param not in help_text:
            print(f"✗ Parameter '{param}' not found in CLI help")
            return False
        print(f"✓ Parameter '{param}' documented in help")

    return True


def run_step3_tests():
    """Run all step 3 hyperparameter tests."""
    print("Running Step 3 hyperparameter compatibility tests...\n")

    tests = [
        ("CLI parameter parsing", test_cli_interactive_commands),
        ("Parameter range validation", test_parameter_ranges),
        ("CLI help documentation", test_cli_help_content),
    ]

    all_passed = True
    for test_name, test_func in tests:
        print(f"--- {test_name} ---")
        if test_func():
            print(f"✓ {test_name} PASSED\n")
        else:
            print(f"✗ {test_name} FAILED\n")
            all_passed = False

    if all_passed:
        print("✅ All Step 3 hyperparameter tests PASSED!")
    else:
        print("❌ Some Step 3 tests FAILED!")

    return all_passed


if __name__ == "__main__":
    run_step3_tests()
