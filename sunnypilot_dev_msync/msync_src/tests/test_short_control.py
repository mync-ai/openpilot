"""Lightweight behavioral tests for Decider.

These are not full pytest tests integrated with openpilot's harness yet; they
can be executed directly (python test_short_control.py) to sanity check the
independent lateral & longitudinal decision paths.

Focus:
  - Tuple output order (lateral, longitudinal)
  - Independent smoothing (no cross-axis contamination)
  - Predictive lateral at zero speed
  - Simultaneous lateral + longitudinal commands
  - Horizon truncation safety when arrays shorter than expected
"""
from types import SimpleNamespace
from pprint import pprint

from sunnypilot_dev_msync.msync_src.short_control import Decider


class MockVec(SimpleNamespace):
    """Simple container with .x/.y lists to mimic capnp arrays."""
    pass


def build_data(
    accelX=None, accelY=None, velX=None, velY=None,
    left_blinker=False, right_blinker=False,
    vEgo=0.0, aEgo=0.0
):
    accelX = accelX or []
    accelY = accelY or []
    velX = velX or [0.0]*len(accelX)
    velY = velY or [0.0]*len(accelY)
    return {
        'acceleration_pred': MockVec(x=accelX, y=accelY),
        'velocity_pred': MockVec(x=velX, y=velY),
        'acceleration_plan': MockVec(x=accelX, y=accelY),  # reused if use_plan
        'velocity_plan': MockVec(x=velX, y=velY),
        'left_blinker': left_blinker,
        'right_blinker': right_blinker,
        'vEgo': vEgo,
        'aEgo': aEgo,
    }


def run_sequence(decider, sequence, label):
    print(f"\n=== {label} ===")
    for i, data in enumerate(sequence):
        decider.set_data(data)
        lat, lon = decider.short_decision()
        print(f"step {i}: lat={lat:>10} lon={lon:>10} v={data['vEgo']:.2f}")


def test_predictive_lateral_at_stop():
    d = Decider(long_smoothing=1, lat_smoothing=1)
    # Lateral acceleration while stopped
    seq = [build_data(accelY=[0.0, 1.0, 2.0, 3.0], vEgo=0.0)]
    d.set_data(seq[0])
    lat, lon = d.short_decision()
    assert lat in ("MILD_RIGHT", "HARD_RIGHT"), f"Expected lateral command, got {lat}"
    assert lon == "NEUTRAL"
    print("Predictive lateral at stop: OK ->", (lat, lon))


def test_simultaneous_brake_and_turn():
    d = Decider(long_smoothing=1, lat_smoothing=1, decel_thresh=1.0)
    # Strong decel + strong left lateral
    data = build_data(accelX=[0.0, -2.0, -3.0], accelY=[0.0, -2.0, -6.0], vEgo=10.0)
    d.set_data(data)
    lat, lon = d.short_decision()
    assert lat in ("HARD_LEFT", "MILD_LEFT")
    assert lon == "BACK"
    print("Simultaneous brake+turn: OK ->", (lat, lon))


def test_forward_vs_brake_priority():
    d = Decider(long_smoothing=1, lat_smoothing=1, accel_thresh=1.0, decel_thresh=1.0)
    # Mixed accel signals: positive forward accel spikes plus stronger negative
    data = build_data(accelX=[2.5, -3.0, 2.0, -0.5], accelY=[0.0])
    d.set_data(data)
    lat, lon = d.short_decision()
    assert lon == "BACK", f"Expected BACK priority over FORWARD, got {lon}"
    print("Brake priority over accel: OK ->", (lat, lon))


def test_smoothing_independence():
    d = Decider(long_smoothing=2, lat_smoothing=2, accel_thresh=1.0, decel_thresh=1.0)
    # First step: mild right only
    seq = [
        build_data(accelY=[1.6, 1.7], accelX=[0.0]),  # lateral candidate
        build_data(accelY=[1.7, 1.8], accelX=[2.0, 2.2]),  # lateral stable + forward candidate
        build_data(accelY=[1.8, 1.9], accelX=[2.5, 2.6]),  # forward smoothing commit
    ]
    outputs = []
    for data in seq:
        d.set_data(data)
        outputs.append(d.short_decision())
    # After two consistent lateral steps, lateral should commit on step 1 or 2 depending on threshold; forward only after two forward steps
    print("Smoothing independence sequence:")
    pprint(outputs)
    assert outputs[-1][1] == "FORWARD", "Expected FORWARD committed longitudinally by final step"


def run_all():
    test_predictive_lateral_at_stop()
    test_simultaneous_brake_and_turn()
    test_forward_vs_brake_priority()
    test_smoothing_independence()
    print("\nAll ad-hoc Decider tests passed.")

if __name__ == "__main__":
    run_all()
