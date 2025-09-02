from openpilot.selfdrive.telemetryd.sub_fields import *
import sys

subscriptions = ['carState', 'controlsState', 'modelV2', 'longitudinalPlan', 'seatControl', 'gpsLocation']
# SubMaster subscribes to selected message types
sm = messaging.SubMaster(subscriptions)

def get_gps():
    sm.update()
    if sm.updated['gpsLocation']:
        gps = sm['gpsLocation']
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
    sm.update()
    if sm.updated['livePose']:
        pose = sm['livePose']
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
    sm.update()
    lat_out = "neutral"
    long_out = "neutral"
    if sm.updated['seatControl']:
        lat_cmd = sm['seatControl'].lateralCommand
        long_cmd = sm['seatControl'].longitudinalCommand

        if lat_cmd == "mildLeft":
            lat_out = "mildLeft"
        elif lat_cmd == "hardLeft":
            lat_out = "hardLeft"
        elif lat_cmd == "hardRight":
            lat_out = "hardRight"
        elif lat_cmd == "mildRight":
            lat_out = "mildRight"
        elif lat_cmd == "neutral":
            lat_out = "neutral"

        if long_cmd == "neutral":
            long_out = "neutral"
        elif long_cmd == "forward":
            long_out = "forward"
        elif long_cmd == "back":
            long_out = "back"
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
