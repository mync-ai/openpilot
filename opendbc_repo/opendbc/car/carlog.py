import os
import logging

# set up logging
LOGPRINT = os.environ.get('LOGPRINT', 'INFO').upper()
carlog = logging.getLogger('carlog')
carlog.setLevel(LOGPRINT)
carlog.propagate = False

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))
carlog.addHandler(handler)

# customize our logging
telemetry_log = logging.getLogger('telemetry_log')
logging.addLevelName(25, "TELEMETRY");telemetry_log.setLevel("TELEMETRY")
telemetry_log.propagate = False

# telemetry_handler = logging.handlers.SocketHandler('172.20.10.14', 9999)
telemetry_handler = logging.FileHandler("/data/openpilot/telemetry.log", mode='a', encoding='utf-8', delay=True)
telemetry_handler.setFormatter(logging.Formatter('%(message)s'))
telemetry_log.addHandler(telemetry_handler)