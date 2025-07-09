import os
import logging
import logging.handlers
import socket

import time
import cereal.messaging as messaging

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
        self.socket.connect((ip, port))
        # print(f"Connected to {ip}:{port}")
        # return s
        return
      except (OSError, socket.error) as e:
        # print(f"Connection failed: {e}. Retrying in {retry_delay}s...")
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

  while True:
    TCP1_channel.connect("172.20.10.14", 9999, retry_delay=2)
    tel_idx = 0
    try:
      while True:
        msg = str(curr_time())+" test_"+str(tel_idx)
        TCP1_channel.socket.sendall(msg.encode('utf-8'))
        tel_idx += 1
        print(f"Sent: {tel_idx}")
        time.sleep(1)
    except (BrokenPipeError, ConnectionResetError, OSError) as e:
      # print(f"Connection lost: {e}")
      TCP1_channel.socket.close()
      # print("Reconnecting...")
      time.sleep(1)

if __name__ == "__main__":
    main()
