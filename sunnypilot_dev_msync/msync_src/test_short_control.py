#!/usr/bin/env python3
"""Simple subscriber to print seat control commands at ~20 Hz."""

from __future__ import annotations

import time

import cereal.messaging as messaging
from cereal import custom


CMD_TELEMETRY = {
    int(custom.SeatControl.SeatControlCommand.neutral): "neutral",
    int(custom.SeatControl.SeatControlCommand.mildForward): "mild_forward",
    int(custom.SeatControl.SeatControlCommand.mildBack): "mild_back",
    int(custom.SeatControl.SeatControlCommand.hardForward): "hard_forward",
    int(custom.SeatControl.SeatControlCommand.hardBack): "hard_back",
    int(custom.SeatControl.SeatControlCommand.mildLeft): "mild_left",
    int(custom.SeatControl.SeatControlCommand.mildRight): "mild_right",
    int(custom.SeatControl.SeatControlCommand.hardLeft): "hard_left",
    int(custom.SeatControl.SeatControlCommand.hardRight): "hard_right",
}


def main() -> None:
    sub_seat = messaging.SubMaster(["seatControl"])
    try:
        while True:
            sub_seat.update()
            lat_cmd = "n/a"
            long_cmd = "n/a"
            if sub_seat.updated["seatControl"]:
                msg = sub_seat["seatControl"]
                lat_cmd = msg.lateralCommand
                long_cmd = msg.longitudinalCommand

            print(f"lat={lat_cmd} long={long_cmd}")
            time.sleep(1 / 20)
    except KeyboardInterrupt:
        print("\nStopped seat control monitor.")


if __name__ == "__main__":
    main()
