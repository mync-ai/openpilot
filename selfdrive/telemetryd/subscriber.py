from openpilot.selfdrive.telemetryd.sub_fields import *
import sys

cmd_telemetry = {'mildForward':'a', 'mildBack':'b', 'hardForward':'A', 'hardBack':'B', 'mildLeft':'l',
                 'mildRight':'r', 'hardLeft':'L', 'hardRight':'R', 'neutral':'N'}
subscriptions = ['carState', 'controlsState', 'modelV2', 'longitudinalPlan', 'seatControl', 'gpsLocation']
# SubMaster subscribes to selected message types
sub_gps = messaging.SubMaster(subscriptions)
sub_imu = messaging.SubMaster(subscriptions)
sub_seat = messaging.SubMaster(subscriptions)

def get_gps():
    sub_gps.update()
    if sub_gps.updated['gpsLocation']:
        gps = sub_gps['gpsLocation']
        gps_out = {
            'timestamp': gps.unixTimestampMillis,
            'latitude': gps.latitude,
            'longitude': gps.longitude,
            'vertical_accuracy': gps.verticalAccuracy,
            'horizontal_accuracy': gps.horizontalAccuracy,
            'speed': gps.speed
        }
        gps_msg = str(gps_out)
        gps_msg = gps_msg.replace('{', '').replace('}', '').replace(',', ' ')
        return gps_msg

def get_imu():
    sub_imu.update()
    if sub_imu.updated['livePose']:
        pose = sub_imu['livePose']
        vel = pose.velocityDevice
        accel = pose.accelerationDevice
        angular = pose.angularVelocityDevice
        orient = pose.orientationNED
        pose_out = {
            'vX': vel.x,
            'vY': vel.y,
            'vZ': vel.z,
            'aX': accel.x,
            'aY': accel.y,
            'aZ': accel.z,
            'wX': angular.x,
            'wY': angular.y,
            'wZ': angular.z,
            'roll': orient.x,
            'pitch': orient.y,
            'yaw': orient.z
        }
        imu_msg = str(pose_out)
        imu_msg = imu_msg.replace('{', '').replace('}', '').replace(',', ' ')
        return imu_msg

def get_short_control():
    sub_seat.update()
    lat_out = "neutral"
    long_out = "neutral"
    if sub_seat.updated['seatControl']:
        lat_cmd = sub_seat['seatControl'].lateralCommand
        long_cmd = sub_seat['seatControl'].longitudinalCommand
        lat_out = cmd_telemetry.get(lat_cmd, "N/A")
        long_out = cmd_telemetry.get(long_cmd, "N/A")
        # if lat_cmd == "mildLeft":
        #     lat_out = "mildLeft"
        # elif lat_cmd == "hardLeft":
        #     lat_out = "hardLeft"
        # elif lat_cmd == "hardRight":
        #     lat_out = "hardRight"
        # elif lat_cmd == "mildRight":
        #     lat_out = "mildRight"
        # elif lat_cmd == "neutral":
        #     lat_out = "neutral"

        # if long_cmd == "neutral":
        #     long_out = "neutral"
        # elif long_cmd == "forward":
        #     long_out = "forward"
        # elif long_cmd == "back":
        #     long_out = "back"
    else:
        return "N/A", "N/A"
    return lat_out, long_out

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
