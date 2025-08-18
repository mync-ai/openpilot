from openpilot.selfdrive.telemetryd.sub_fields import *
import sys

subscriptions = ['carState', 'controlsState', 'modelV2', 'longitudinalPlan', 'seatControl', 'gpsLocationExternal']
# SubMaster subscribes to selected message types
sm = messaging.SubMaster(subscriptions)

def get_gps():
    sm.update()
    if sm.updated['gpsLocationExternal']:
        gps = sm['gpsLocationExternal']
        gps_out = {
            'latitude': gps.latitude,
            'longitude': gps.longitude,
            'vertical_accuracy': gps.verticalAccuracy,
            'horizontal_accuracy': gps.horizontalAccuracy,
            'speed': gps.speed,
            'timestamp': gps.unixTimestampMillis
        }
        gps_out['timestamp'] = gps_out['timestamp'] / 1000.0   #convert from ms to s
        return gps_out

def get_short_control():
    cmd_out = "neutral"
    sm.update()
    if sm.updated['seatControl']:
        cmd_val = sm['seatControl'].command
        if cmd_val == "mildLeft" or cmd_val == "hardLeft":
            cmd_out = "left"
        elif cmd_val == "mildRight" or cmd_val == "hardRight":
            cmd_out = "right"
        elif cmd_val == "neutral":
            cmd_out = "neutral"
        elif cmd_val == "forward":
            cmd_out = "forward"
        elif cmd_val == "back":
            cmd_out = "back"
        return cmd_out

# if __name__ == "__main__":
#     latency = 0.1  # seconds, change as needed
#     interesting_subs = ['longitudinalPlan', 'modelV2']
#     parse_messages(interesting_subs, latency, verbose=True)


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