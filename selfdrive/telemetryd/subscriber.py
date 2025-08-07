from openpilot.selfdrive.telemetryd.sub_fields import *
import sys

subscriptions = ['carState', 'controlsState', 'modelV2', 'longitudinalPlan', 'seatControl']
# SubMaster subscribes to selected message types
sm = messaging.SubMaster(subscriptions)


def print_model(sub, prev_conf=None):
    """
    Reads and processes perception-prediction model messages.
    """
    conf_dict = {"red": "Low   ", "yellow": "Medium", "green": "High  "}
    conf_str = conf_dict.get(sub.confidence, str(sub.confidence))
    if prev_conf is None:
        print("Model Confidence: ", end="", flush=True)
    if conf_str != prev_conf:
        sys.stdout.write("\rModel Confidence: {}".format(conf_str))
        sys.stdout.flush()
    return conf_str


def print_plan(sub_long, prev_value=None):
    """
    Reads and processes longitudinal plan messages.
    """
    if prev_value is None:
        print("Planned Long Acceleration: ")
        print("Seat Signal: ")
    value = sub_long.accels
    jerks = sub_long.jerks
    display_value = []
    for a in value:
        val_str = f"{a:+.2f}"
        if len(val_str) > 5:
            val_str = val_str[:5]
        else:
            val_str = val_str.ljust(5, '0')
        display_value.append(val_str)
    # Determine seat signal using average jerk
    avg_jerk = sum(jerks) / len(jerks) if len(jerks) > 0 else 0.0
    if avg_jerk > 0.5:
        seat_signal = "Lean Forward"
    elif avg_jerk < -0.5:
        seat_signal = "Lean Back"
    else:
        seat_signal = "Neutral"
    # Only update if changed
    if display_value != prev_value:
        # Move cursor up 2 lines, clear both lines, print both lines (no extra newlines)
        sys.stdout.write("\033[2F")  # Move up 2 lines
        sys.stdout.write(f"\033[2KPlanned Long Acceleration: [{', '.join(display_value)}]\n")
        sys.stdout.write(f"\033[2KSeat Signal: {seat_signal}\n")
        sys.stdout.flush()
    return display_value


def print_ego_state(sub):
    """
    Reads and processes ego vehicle status messages.
    """
    print("Processing ego state...")

def listen_plan(sub_long):
    # vectors are length 17 and span the plan from 0 to 2.5 seconds
    accelerations = sub_long.accels
    jerks = sub_long.jerks # derivative of acceleration
    return accelerations, jerks

def parse_messages(interesting_subs, latency, verbose=False):
    print("Starting MSync parsing...\n")
    print("                             0s                     0.5s                   1.0s                   1.5s                   2.0s                   2.5s")
    prev_accel = None
    # prev_conf = None
    while True:
        sm.update()
        if verbose:
            if sm.updated['modelV2'] and 'modelV2' in interesting_subs:
                model_sub = sm['modelV2']
                # prev_conf = print_model(model_sub, prev_conf)
            if sm.updated['longitudinalPlan'] and 'longitudinalPlan' in interesting_subs:
                long_sub = sm['longitudinalPlan']
                prev_accel = print_plan(long_sub, prev_accel)

        listen_plan(sm['longitudinalPlan'])
        time.sleep(latency)

def get_cereal_data(interesting_subs=['longitudinalPlan', 'modelV2'], verbose=False):
    prev_accel = None
    prev_conf = None
    sm.update()
    if verbose:
        if sm.updated['modelV2'] and 'modelV2' in interesting_subs:
            model_sub = sm['modelV2']
            prev_conf = print_model(model_sub, prev_conf)
        if sm.updated['longitudinalPlan'] and 'longitudinalPlan' in interesting_subs:
            long_sub = sm['longitudinalPlan']
            prev_accel = print_plan(long_sub, prev_accel)

    return listen_plan(sm['longitudinalPlan'])

def get_short_control():
    sm.update()
    if sm.updated['seatControl']:
        cmd = sm['seatControl'].command
        if cmd.endswith("Left"):
            cmd = "left"
        elif cmd.endswith("Right"):
            cmd = "right"
        return cmd

# if __name__ == "__main__":
#     latency = 0.1  # seconds, change as needed
#     interesting_subs = ['longitudinalPlan', 'modelV2']
#     parse_messages(interesting_subs, latency)


# Model Outputs:
# laneLines
# orientationRate
# velocity
# orientation
# position
# laneLineProbs
# roadEdges
# meta
# acceleration
# laneLineStds
# roadEdgeStds
# modelExecutionTime
# leadsV3
# confidence