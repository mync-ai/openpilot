#!/usr/bin/env python3
'''
OpenPilot Log Analyzer

This script reads rlogs from an openpilot route and prints message data chronologically
with their timestamps. It focuses on key message topics including ModelDataV2, carState,
carControl, longitudinalPlan, radarState, and seatControl.

For seat control commands, it also tracks and prints the duration of each command.

Usage:
    python analyze_logs.py <route_or_log_path> [--topics topic1,topic2,...] [--max-messages N]

Examples:
    python analyze_logs.py "a2a0ccea32023010|2023-01-01--12-00-00"
    python analyze_logs.py /path/to/log/file.bz2 --topics modelV2,carState
    python analyze_logs.py route_name --max-messages 1000
'''

import argparse
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Add the openpilot root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.lib.logreader import LogReader
from cereal import log


class SeatControlTracker:
    """Tracks seat control commands and their durations."""

    def __init__(self):
        self.current_command = None
        self.command_start_time = None
        self.command_durations = []

    def update(self, timestamp: int, command: str, source: str) -> Optional[Dict]:
        """
        Update the seat control state and return duration info if command changed.

        Args:
            timestamp: Message timestamp in nanoseconds
            command: Current seat control command
            source: Source of the command

        Returns:
            Dict with duration info if command changed, None otherwise
        """
        if self.current_command != command:
            duration_info = None

            # If we had a previous command, calculate its duration
            if self.current_command is not None and self.command_start_time is not None:
                duration_ns = timestamp - self.command_start_time
                duration_ms = duration_ns / 1e6
                duration_info = {
                    'previous_command': self.current_command,
                    'duration_ms': duration_ms,
                    'end_timestamp': timestamp
                }
                self.command_durations.append(duration_info)

            # Update to new command
            self.current_command = command
            self.command_start_time = timestamp

            return duration_info

        return None


class LogAnalyzer:
    """Analyzes openpilot logs and prints chronological message data."""

    def __init__(self, log_path: str, topics: List[str], max_messages: Optional[int] = None):
        self.log_path = log_path
        self.topics = set(topics)
        self.max_messages = max_messages
        self.seat_tracker = SeatControlTracker()

        # Message counters
        self.message_counts = defaultdict(int)
        self.total_messages = 0

    def format_timestamp(self, timestamp_ns: int) -> str:
        """Convert nanosecond timestamp to human-readable format."""
        timestamp_s = timestamp_ns / 1e9
        dt = datetime.fromtimestamp(timestamp_s)
        return f"{dt.strftime('%H:%M:%S')}.{int((timestamp_ns % 1e9) / 1e6):03d}"

    def format_modelv2_data(self, msg) -> str:
        """Format ModelDataV2 message for display."""
        model = msg.modelV2
        lines = []

        # Basic info
        lines.append(f"  frameId: {model.frameId}")
        lines.append(f"  frameAge: {model.frameAge}")
        lines.append(f"  frameDropPerc: {model.frameDropPerc:.2f}")

        # Velocity and acceleration predictions
        if hasattr(model, 'velocity') and model.velocity:
            vel = model.velocity
            lines.append(f"  velocity: x=[{', '.join(f'{x:.2f}' for x in vel.x[:5])}...] t=[{', '.join(f'{t:.2f}' for t in vel.t[:5])}...]")

        if hasattr(model, 'acceleration') and model.acceleration:
            acc = model.acceleration
            lines.append(f"  acceleration: x=[{', '.join(f'{x:.2f}' for x in acc.x[:5])}...] t=[{', '.join(f'{t:.2f}' for t in acc.t[:5])}...]")

        # Position predictions
        if hasattr(model, 'position') and model.position:
            pos = model.position
            lines.append(f"  position: x=[{', '.join(f'{x:.2f}' for x in pos.x[:3])}...] y=[{', '.join(f'{y:.2f}' for y in pos.y[:3])}...]")

        return '\n'.join(lines)

    def format_carstate_data(self, msg) -> str:
        """Format CarState message for display."""
        car = msg.carState
        lines = []

        lines.append(f"  vEgo: {car.vEgo:.2f} m/s")
        lines.append(f"  aEgo: {car.aEgo:.2f} m/s²")
        lines.append(f"  steeringAngleDeg: {car.steeringAngleDeg:.1f}°")
        lines.append(f"  steeringTorque: {car.steeringTorque:.1f} Nm")
        lines.append(f"  gas: {car.gas:.3f}, brake: {car.brake:.3f}")
        lines.append(f"  blinkers: L={car.leftBlinker}, R={car.rightBlinker}")
        lines.append(f"  gearShifter: {car.gearShifter}")

        if hasattr(car, 'wheelSpeeds'):
            ws = car.wheelSpeeds
            lines.append(f"  wheelSpeeds: FL={ws.fl:.1f} FR={ws.fr:.1f} RL={ws.rl:.1f} RR={ws.rr:.1f}")

        return '\n'.join(lines)

    def format_carcontrol_data(self, msg) -> str:
        """Format CarControl message for display."""
        control = msg.carControl
        lines = []

        lines.append(f"  enabled: {control.enabled}")
        lines.append(f"  active: {control.active}")

        if hasattr(control, 'actuators'):
            act = control.actuators
            lines.append(f"  actuators:")
            lines.append(f"    steer: {act.steer:.3f}, steerOutputCan: {act.steerOutputCan:.3f}")
            lines.append(f"    accel: {act.accel:.3f}, brake: {act.brake:.3f}")
            lines.append(f"    gas: {act.gas:.3f}")

        if hasattr(control, 'hudControl'):
            hud = control.hudControl
            lines.append(f"  hudControl:")
            lines.append(f"    speedVisible: {hud.speedVisible}")
            lines.append(f"    lanesVisible: {hud.lanesVisible}")
            lines.append(f"    leadVisible: {hud.leadVisible}")

        return '\n'.join(lines)

    def format_longitudinalplan_data(self, msg) -> str:
        """Format LongitudinalPlan message for display."""
        plan = msg.longitudinalPlan
        lines = []

        if hasattr(plan, 'speeds') and plan.speeds:
            speeds = plan.speeds[:5]  # First 5 values
            lines.append(f"  speeds: [{', '.join(f'{s:.2f}' for s in speeds)}...]")

        if hasattr(plan, 'accels') and plan.accels:
            accels = plan.accels[:5]  # First 5 values
            lines.append(f"  accels: [{', '.join(f'{a:.2f}' for a in accels)}...]")

        if hasattr(plan, 'jerks') and plan.jerks:
            jerks = plan.jerks[:5]  # First 5 values
            lines.append(f"  jerks: [{', '.join(f'{j:.2f}' for j in jerks)}...]")

        lines.append(f"  hasLead: {plan.hasLead}")
        if hasattr(plan, 'longitudinalPlanSource'):
            lines.append(f"  source: {plan.longitudinalPlanSource}")

        return '\n'.join(lines)

    def format_radarstate_data(self, msg) -> str:
        """Format RadarState message for display."""
        radar = msg.radarState
        lines = []

        if hasattr(radar, 'leadOne'):
            lead = radar.leadOne
            lines.append(f"  leadOne:")
            lines.append(f"    dRel: {lead.dRel:.1f}m, vRel: {lead.vRel:.1f}m/s")
            lines.append(f"    status: {lead.status}, radar: {lead.radar}")

        if hasattr(radar, 'leadTwo'):
            lead2 = radar.leadTwo
            if lead2.status:
                lines.append(f"  leadTwo:")
                lines.append(f"    dRel: {lead2.dRel:.1f}m, vRel: {lead2.vRel:.1f}m/s")
                lines.append(f"    status: {lead2.status}")

        return '\n'.join(lines)

    def format_seatcontrol_data(self, msg) -> str:
        """Format SeatControl message for display."""
        seat = msg.seatControl
        lines = []

        command = str(seat.command)
        source = str(seat.source)
        timestamp = seat.timestamp

        lines.append(f"  command: {command}")
        lines.append(f"  source: {source}")
        lines.append(f"  timestamp: {self.format_timestamp(timestamp)}")

        # Track command duration
        duration_info = self.seat_tracker.update(timestamp, command, source)
        if duration_info:
            lines.append(f"  [DURATION] Previous command '{duration_info['previous_command']}' lasted {duration_info['duration_ms']:.1f}ms")

        return '\n'.join(lines)

    def format_message(self, msg) -> Optional[str]:
        """Format a message for display based on its type."""
        msg_type = msg.which()

        if msg_type not in self.topics:
            return None

        timestamp_str = self.format_timestamp(msg.logMonoTime)

        header = f"[{timestamp_str}] {msg_type.upper()}"

        formatters = {
            'modelV2': self.format_modelv2_data,
            'carState': self.format_carstate_data,
            'carControl': self.format_carcontrol_data,
            'longitudinalPlan': self.format_longitudinalplan_data,
            'radarState': self.format_radarstate_data,
            'seatControl': self.format_seatcontrol_data,
        }

        formatter = formatters.get(msg_type)
        if formatter:
            try:
                body = formatter(msg)
                return f"{header}\n{body}\n"
            except Exception as e:
                return f"{header}\n  [ERROR formatting message: {e}]\n"
        else:
            return f"{header}\n  [No formatter available]\n"

    def analyze(self):
        """Main analysis function."""
        print(f"Analyzing log: {self.log_path}")
        print(f"Topics: {', '.join(sorted(self.topics))}")
        if self.max_messages:
            print(f"Max messages: {self.max_messages}")
        print("-" * 80)

        try:
            lr = LogReader(self.log_path, sort_by_time=True)

            for msg in lr:
                if self.max_messages and self.total_messages >= self.max_messages:
                    break

                formatted = self.format_message(msg)
                if formatted:
                    print(formatted)
                    self.message_counts[msg.which()] += 1
                    self.total_messages += 1

        except Exception as e:
            print(f"Error reading log: {e}")
            return

        # Print summary
        print("-" * 80)
        print("SUMMARY:")
        print(f"Total messages processed: {self.total_messages}")
        for topic, count in sorted(self.message_counts.items()):
            print(f"  {topic}: {count}")

        # Print seat control duration summary
        if self.seat_tracker.command_durations:
            print(f"\nSeat Control Command Durations:")
            for i, duration in enumerate(self.seat_tracker.command_durations):
                print(f"  {i+1}. {duration['previous_command']}: {duration['duration_ms']:.1f}ms")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze OpenPilot rlogs and print message data chronologically',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s "a2a0ccea32023010|2023-01-01--12-00-00"
  %(prog)s /path/to/log/file.bz2 --topics modelV2,carState
  %(prog)s route_name --max-messages 1000 --topics seatControl
        '''
    )

    parser.add_argument('log_path', help='Route name or path to log file')
    parser.add_argument('--topics',
                       default='modelV2,carState,carControl,longitudinalPlan,radarState,seatControl',
                       help='Comma-separated list of message topics to analyze (default: all main topics)')
    parser.add_argument('--max-messages', type=int,
                       help='Maximum number of messages to process')

    args = parser.parse_args()

    # Parse topics
    topics = [topic.strip() for topic in args.topics.split(',') if topic.strip()]

    # Create and run analyzer
    analyzer = LogAnalyzer(args.log_path, topics, args.max_messages)
    analyzer.analyze()


if __name__ == "__main__":
    main()
