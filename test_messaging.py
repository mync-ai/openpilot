#!/usr/bin/env python3
"""
Deprecated test: seatControlConfigRequest messaging removed.
Keeping minimal publisher/subscriber example for seatControl topic only.
"""

import time
import threading
import cereal.messaging as messaging


def publisher_test():
    print("Starting publisher test (seatControl)...")
    pm = messaging.PubMaster(['seatControl'])
    for i in range(3):
        msg = messaging.new_message('seatControl')
        msg.seatControl.command = 0  # neutral
        msg.seatControl.source = 0   # none
        msg.seatControl.timestamp = int(time.time() * 1e9)
        pm.send('seatControl', msg)
        print(f"Sent seatControl message {i+1}")
        time.sleep(1)
    print("Publisher test complete")


def subscriber_test():
    print("Starting subscriber test (seatControl)...")
    sm = messaging.SubMaster(['seatControl'])
    start_time = time.time()
    while time.time() - start_time < 5:
        sm.update()
        if sm.updated['seatControl']:
            m = sm['seatControl']
            print(f"Received seatControl: command={m.seatControl.command} source={m.seatControl.source} ts={m.seatControl.timestamp}")
        time.sleep(0.1)
    print("Subscriber test complete")


def main():
    subscriber_thread = threading.Thread(target=subscriber_test)
    subscriber_thread.start()
    time.sleep(0.5)
    publisher_test()
    subscriber_thread.join()


if __name__ == "__main__":
    main()
