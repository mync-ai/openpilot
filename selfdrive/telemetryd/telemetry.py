import os
import logging
import logging.handlers

import time
import cereal.messaging as messaging

def setup_logging_telemetry():
  # customize our logging
  telemetry_log = logging.getLogger('telemetry_log')
  logging.addLevelName(25, 'TELEMETRY');telemetry_log.setLevel('TELEMETRY')
  telemetry_log.propagate = False

  telemetry_handler = logging.handlers.SocketHandler('172.20.10.14', 9999)
  # telemetry_handler = logging.FileHandler("/data/openpilot/telemetry.log", mode='w', encoding='utf-8', delay=False)
  telemetry_handler.setFormatter(logging.Formatter('%(message)s'))
  telemetry_log.addHandler(telemetry_handler)
  # telemetry_log.log(25, "test telemetry message!\n")

def main():
    tel = setup_logging_telemetry()

    while True:
        tel.log(25, "test telemetry message!\n")
        time.sleep(0.1)

if __name__ == "__main__":
    main()
