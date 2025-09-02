import os
import logging
import logging.handlers
import socket
import threading
import time
from openpilot.selfdrive.telemetryd.subscriber import *

# def setup_logging_telemetry():
#   # customize our logging
#   telemetry_log = logging.getLogger('telemetry_log')
#   logging.addLevelName(25, 'TELEMETRY');telemetry_log.setLevel('TELEMETRY')
#   telemetry_log.propagate = False

  # telemetry_handler = logging.handlers.SocketHandler('172.20.10.14', 9999)
#   # telemetry_handler = logging.FileHandler("/data/openpilot/telemetry.log", mode='w', encoding='utf-8', delay=False)
#   telemetry_handler.setFormatter(logging.Formatter('%(message)s'))
#   telemetry_log.addHandler(telemetry_handler)
#   # telemetry_log.log(25, "test telemetry message!\n")
#   return telemetry_log

def curr_time():
  return time.time_ns() / 1e9
  # return time.perf_counter()

class channel:
  def __init__(self, name:str, msg_type):
    self.name = name
    self.msg_type = msg_type
    self.socket = self.create_socket()
    # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) ?
    # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) ?

  def create_socket(self):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return s

  def connect(self, ip, port, retry_delay=2):
    while True:
      try:
        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print(f"Connecting to {ip}:{port}...")
        self.socket.connect((ip, port))
        # print(f"Connected to {ip}:{port}")
        # return s
        return
      except (OSError, socket.error, socket.timeout) as e:
        print(f"Connection failed: {e}. Retrying in {retry_delay}s...")
        time.sleep(retry_delay)

def main():
  # tel = setup_logging_telemetry()
  # tel_idx = 0
  # while True:
  #     tel.log(25, (str(curr_milli_time())+" test_"+str(tel_idx)+'\n'))
  #     tel_idx += 1
  #     time.sleep(1)

  TCP1_channel = channel("TCP1", "tcp1")
  TCP2_channel = channel("TCP2", "tcp2")
  TCP3_channel = channel("TCP3", "tcp3")

  telemetry_threads = []
  def TCP1_thread():
    while True:
      try:
        TCP1_channel.connect("192.168.1.111", 9999, retry_delay=2)
        while True:
          lat_cmd, long_cmd = get_short_control()
          print(f"Received: {lat_cmd}, {long_cmd}")
          if lat_cmd != "N/A" and long_cmd != "N/A":
            msg = lat_cmd + " " + long_cmd
          else:
            msg = "Invalid data"
          msg = str(curr_time()) + " " + msg + " "
          TCP1_channel.socket.sendall(msg.encode('utf-8'))
          time.sleep(0.05)
      except (BrokenPipeError, ConnectionResetError, OSError) as e:
        print(f"TCP1 connection lost: {e}")
        TCP1_channel.socket.close()
        TCP1_channel.socket = TCP1_channel.create_socket()
        print("TCP1 reconnecting...")
        time.sleep(1)

  def TCP2_thread():
    while True:
      TCP2_channel.connect("192.168.1.111", 9998, retry_delay=2)
      try:
        while True:
          gpsinfo = get_gps()
          if not gpsinfo:
            gpsinfo = ""
          TCP2_channel.socket.sendall(gpsinfo.encode('utf-8'))
          time.sleep(1)
      except (BrokenPipeError, ConnectionResetError, OSError) as e:
        print(f"TCP2 Connection lost: {e}")
        TCP2_channel.socket.close()
        TCP2_channel.socket = TCP2_channel.create_socket()
        print("TCP2 reconnecting...")
        time.sleep(1)

  def TCP3_thread():
    while True:
      TCP3_channel.connect("192.168.1.111", 9997, retry_delay=2)
      try:
        while True:
          imu_info = get_imu()
          if not imu_info:
            imu_info = ""
          print(imu_info)
          TCP3_channel.socket.sendall(imu_info.encode('utf-8'))
          time.sleep(1)
      except (BrokenPipeError, ConnectionResetError, OSError) as e:
        print(f"TCP3 Connection lost: {e}")
        TCP3_channel.socket.close()
        TCP3_channel.socket = TCP3_channel.create_socket()
        print("TCP3 reconnecting...")
        time.sleep(0.05)

  telemetry_threads.append(threading.Thread(target=TCP1_thread))
  telemetry_threads.append(threading.Thread(target=TCP2_thread))
  telemetry_threads.append(threading.Thread(target=TCP3_thread))

  for thread in telemetry_threads:
    thread.start()

  # while True:
  #   TCP1_channel.connect("192.168.1.111", 9999, retry_delay=2)
  #   try:
  #     while True:
  #       cmd = get_short_control()
  #       print(f"Received: {cmd}")
  #       if cmd:
  #         msg = cmd
  #       else:
  #         msg = " Invalid data"
  #       msg = str(curr_time()) + " " + msg + "\n"

  #       # msg = str(curr_time())+" test_"+str(tel_idx)

  #       TCP1_channel.socket.sendall(msg.encode('utf-8'))
  #       # tel_idx += 1
  #       # print(f"Sent: {tel_idx}")
  #       time.sleep(0.05)
  #   except (BrokenPipeError, ConnectionResetError, OSError) as e:
  #     print(f"Connection lost: {e}")
  #     TCP1_channel.socket.close()
  #     TCP1_channel.socket = TCP1_channel.create_socket()
  #     print("Reconnecting...")
  #     time.sleep(1)

if __name__ == "__main__":
    main()