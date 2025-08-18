#!/usr/bin/env python3
"""Step 2 integration test: verify service handles tuple return correctly."""

import sys
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, '/home/kerrb/msync_branching/openpilot')

from sunnypilot_dev_msync.msync_src.short_control import Decider
from sunnypilot_dev_msync.msync_src.parameter_manager import SeatControlParameterManager
from sunnypilot_dev_msync.msync_src.seat_control_service_enhanced import EnhancedSeatControlService


def test_parameter_manager_new_params():
    """Test parameter manager handles new parameter names."""
    pm = SeatControlParameterManager()
    config = pm.get_current_config()

    # Check that new parameters exist
    required_params = ['accel_thresh', 'decel_thresh', 'long_smoothing', 'lat_smoothing']
    for param in required_params:
        assert param in config, f"Missing parameter: {param}"

    # Check that old parameters are removed
    old_params = ['long_thresh', 'smoothing_window']
    for param in old_params:
        assert param not in config, f"Old parameter still present: {param}"

    print("✓ Parameter manager updated correctly")


def test_decider_creation():
    """Test that Decider can be created with new parameter names."""
    pm = SeatControlParameterManager()
    config = pm.get_current_config()

    # This should not raise an exception
    decider = Decider(
        turn_thresh_1=config['turn_thresh_1'],
        turn_thresh_2=config['turn_thresh_2'],
        accel_thresh=config['accel_thresh'],
        decel_thresh=config['decel_thresh'],
        long_smoothing=config['long_smoothing'],
        lat_smoothing=config['lat_smoothing'],
        horizon=config['horizon'],
        use_plan=config['use_plan']
    )

    # Test that it returns a tuple
    mock_data = {
        'acceleration_pred': SimpleNamespace(x=[0.0], y=[0.0]),
        'velocity_pred': SimpleNamespace(x=[0.0], y=[0.0]),
        'acceleration_plan': SimpleNamespace(x=[0.0], y=[0.0]),
        'velocity_plan': SimpleNamespace(x=[0.0], y=[0.0]),
        'left_blinker': False,
        'right_blinker': False,
        'vEgo': 0.0,
        'aEgo': 0.0,
    }

    decider.set_data(mock_data)
    result = decider.short_decision()

    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2, f"Expected 2 elements, got {len(result)}"

    lateral, longitudinal = result
    assert isinstance(lateral, str), f"Expected string for lateral, got {type(lateral)}"
    assert isinstance(longitudinal, str), f"Expected string for longitudinal, got {type(longitudinal)}"

    print(f"✓ Decider returns tuple: {result}")


def test_service_creation():
    """Test that EnhancedSeatControlService can be created with new parameters."""
    pm = SeatControlParameterManager()
    config = pm.get_current_config()

    # Mock messaging to avoid actual message bus dependencies
    with patch('sunnypilot_dev_msync.msync_src.seat_control_service_enhanced.messaging'):
        service = EnhancedSeatControlService(initial_config=config)

        # Test that components can be created
        service._create_components()

        assert service.decider is not None, "Decider was not created"
        assert service.publisher is not None, "Publisher was not created"

        print("✓ Service components created successfully")


def test_integration_mock_messaging():
    """Test the integration with mocked messaging."""
    from sunnypilot_dev_msync.msync_src.seat_control_integration import SeatControlPublisher

    # Mock the messaging system
    with patch('sunnypilot_dev_msync.msync_src.seat_control_integration.messaging') as mock_messaging:
        mock_pm = Mock()
        mock_submaster = Mock()

        # Create decider with correct parameters
        pm = SeatControlParameterManager()
        config = pm.get_current_config()

        decider = Decider(
            turn_thresh_1=config['turn_thresh_1'],
            turn_thresh_2=config['turn_thresh_2'],
            accel_thresh=config['accel_thresh'],
            decel_thresh=config['decel_thresh'],
            long_smoothing=config['long_smoothing'],
            lat_smoothing=config['lat_smoothing'],
            horizon=config['horizon'],
            use_plan=config['use_plan']
        )

        # Create publisher
        publisher = SeatControlPublisher(decider, mock_submaster, update_frequency=1)

        assert publisher.decider is not None
        assert publisher.submaster is not None

        print("✓ Integration components created successfully")


def run_all_tests():
    """Run all step 2 integration tests."""
    print("Running Step 2 integration tests...")

    test_parameter_manager_new_params()
    test_decider_creation()
    test_service_creation()
    test_integration_mock_messaging()

    print("\n✓ All Step 2 integration tests passed!")


if __name__ == "__main__":
    run_all_tests()
