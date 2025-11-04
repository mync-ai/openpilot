import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import sunnypilot_dev_msync.msync_src.short_control as short_control
import time
import cereal.messaging as messaging


def extract_data(sm, interesting_subs):
    """
    Extracts key data from model and car state messages.

    Returns:
        dict: Dictionary containing:
            - acceleration: ModelV2 acceleration data (XYZTData)
            - confidence: ModelV2 confidence value
            - left_blinker: Left blinker state from carState
            - right_blinker: Right blinker state from carState
    """
    result = {
        'acceleration_pred': None,
        'velocity_pred': None,
        'acceleration_plan': None,
        'velocity_plan': None,
        'confidence': None,
        'left_blinker': None,
        'right_blinker': None,
        'gear_shifter': None
    }

    # Extract model data
    if 'modelV2' in interesting_subs and sm.updated['modelV2']:
        model_sub = sm['modelV2']
        if hasattr(model_sub, 'acceleration'):
            result['acceleration_pred'] = model_sub.acceleration
        if hasattr(model_sub, 'velocity'):
            result['velocity_pred'] = model_sub.velocity
        if hasattr(model_sub, 'confidence'):
            result['confidence'] = model_sub.confidence

    # Extract longitudinal plan data
    if 'longitudinalPlan' in interesting_subs and sm.updated['longitudinalPlan']:
        plan_sub = sm['longitudinalPlan']
        if hasattr(plan_sub, 'accels') and hasattr(plan_sub, 'speeds'):
            # Create plan data structures similar to model predictions
            # Note: longitudinalPlan provides 1D arrays, we need to create compatible structures
            class PlanData:
                def __init__(self, x_data):
                    self.x = x_data
                    self.y = [0.0] * len(x_data)  # No Y component for longitudinal plan

            result['acceleration_plan'] = PlanData(list(plan_sub.accels))
            result['velocity_plan'] = PlanData(list(plan_sub.speeds))


    # Extract car state data
    if 'carState' in interesting_subs and sm.updated['carState']:
        car_sub = sm['carState']
        if hasattr(car_sub, 'leftBlinker'):
            result['left_blinker'] = car_sub.leftBlinker
        if hasattr(car_sub, 'rightBlinker'):
            result['right_blinker'] = car_sub.rightBlinker
        if hasattr(car_sub, 'vEgo'):
            result['vEgo'] = car_sub.vEgo
        if hasattr(car_sub, 'aEgo'):
            result['aEgo'] = car_sub.aEgo
        if hasattr(car_sub, 'gearShifter'):
            result['gear_shifter'] = car_sub.gearShifter

    return result


def execute_control(decider, submaster, interesting_subs=['modelV2', 'carState'], latency=0.5):
    """
    Execute control loop that listens to topics, extracts data, and calls seat_control.
    """
    print("Starting seat control execution...")
    while True:
        submaster.update()

        # Extract data from subscribed topics
        data = extract_data(submaster, interesting_subs)

        # Only check for essential data that we actually need
        required_data = ['acceleration_pred', 'velocity_pred', 'left_blinker', 'right_blinker', 'vEgo', 'aEgo', 'gear_shifter']
        has_required_data = all(data.get(key) is not None for key in required_data)

        if has_required_data:
            # Set default values for plan data if not available
            if data['acceleration_plan'] is None:
                data['acceleration_plan'] = data['acceleration_pred']  # Use pred as fallback
            if data['velocity_plan'] is None:
                data['velocity_plan'] = data['velocity_pred']  # Use pred as fallback

            decider.set_data(data)
            # Call seat control with extracted data
            response = decider.short_decision()
            yield response
        # else:
        #     print(f"Missing required data: {[key for key in required_data if data.get(key) is None]}")

        # Sleep for specified latency
        time.sleep(latency)


if __name__ == "__main__":
    latency = 0.05  # seconds, change as needed

    # Parsing options: 'modelV2', 'longitudinalPlan', 'radarState', 'carControl', 'carState'
    interesting_subs = ['modelV2', 'carState']
    subscriptions = ['carState', 'carControl', 'modelV2', 'longitudinalPlan', 'radarState']
    # SubMaster subscribes to selected message types
    sm = messaging.SubMaster(subscriptions)

    decider = short_control.Decider(
        turn_thresh_1=1.0,
        turn_thresh_2=2.5,
        accel_thresh=2.0,
        decel_thresh=2.0,
        long_sens=3,
        lat_sens=3,
        long_sticky=3,
        lat_sticky=3,
        long_horizon=3,
        long_horizon_offset=3,
        lat_horizon=3,
        lat_horizon_offset=3,
        use_plan=False,
        lockout_speed=2.5,
    )
    # Set verbose=True to see detailed field-by-field output
    # Set verbose=False to use the original compact display format
    # parse_messages(interesting_subs, latency, verbose=True)
    for control_response in execute_control(decider, sm, interesting_subs, latency):
        print(f"Lateral: {control_response[0]} | Longitudinal: {control_response[1]}        ", end='\r')
