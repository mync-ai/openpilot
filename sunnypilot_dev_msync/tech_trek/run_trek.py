#!/usr/bin/env python3
"""
Trek Runner Module

This module loads a CSV file containing timestamps and commands, then publishes
seat control commands when the current timestamp matches entries in the CSV.
"""
from helper import ns_to_ms, map_command_to_seat_control
import sys
import time
import pandas as pd
import os
from cereal import messaging


def load_csv_commands(filename):
    """Load commands from CSV file and return as a dictionary with timestamps as keys"""
    try:
        # Check if file exists in data directory first
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, 'data')

        # Try data directory first, then current directory, then absolute path
        possible_paths = [
            os.path.join(data_dir, filename),
            filename
        ]

        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break

        if not file_path:
            raise FileNotFoundError(f"CSV file not found: {filename}")

        print(f"Loading CSV from: {file_path}")
        df = pd.read_csv(file_path)

        if 'timestamp' not in df.columns or 'command' not in df.columns:
            raise ValueError("CSV must contain 'timestamp' and 'command' columns")

        # Convert to dictionary for fast lookup
        commands_dict = {}
        for _, row in df.iterrows():
            timestamp_ms = int(row['timestamp'])  # Convert to integer milliseconds
            command = row['command']
            commands_dict[timestamp_ms] = command

        print(f"Loaded {len(commands_dict)} commands from CSV")
        return commands_dict

    except Exception as e:
        print(f"Error loading CSV file {filename}: {e}")
        sys.exit(1)


def get_current_timestamp_ms(sm):
    """Get current timestamp in milliseconds from carState"""
    sm.update()
    if sm.updated['carState']:
        timestamp_ns = sm.logMonoTime['carState']
        return ns_to_ms(timestamp_ns)
    return -1


def main():
    if len(sys.argv) != 2:
        print("Usage: python run_trek.py <csv_file>")
        print("  csv_file: CSV file containing timestamps and commands")
        sys.exit(1)

    csv_filename = sys.argv[1]

    # Load CSV commands
    commands_dict = load_csv_commands(csv_filename)

    # Set up messaging
    print("Setting up messaging...")
    pm = messaging.PubMaster(['seatControl'])
    sm = messaging.SubMaster(['carState'])

    print("Starting trek execution...")
    print("Press Ctrl+C to stop")

    # Track executed commands to avoid duplicates
    executed_commands = set()

    # Convert command dict to sorted list for range searching
    sorted_timestamps = sorted(commands_dict.keys())

    # Tolerance window in milliseconds
    TOLERANCE_MS = 20  # 100ms tolerance

    try:
        while True:
            # Get current timestamp
            current_timestamp_ms = get_current_timestamp_ms(sm)

            if current_timestamp_ms > 0:

                # Find commands within tolerance window
                for csv_timestamp in sorted_timestamps:
                    if csv_timestamp in executed_commands:
                        continue

                    # Check if current timestamp is within tolerance of CSV timestamp
                    time_diff = abs(current_timestamp_ms - csv_timestamp)
                    if time_diff <= TOLERANCE_MS:
                        command_char = commands_dict[csv_timestamp]

                        # Map command to seat control
                        lateral_cmd, longitudinal_cmd = map_command_to_seat_control(command_char)

                        # Create and send seat control message
                        seat_control_msg = messaging.new_message('seatControl')
                        seat_control_msg.seatControl.lateralCommand = lateral_cmd
                        seat_control_msg.seatControl.longitudinalCommand = longitudinal_cmd
                        seat_control_msg.seatControl.timestamp = int(time.time() * 1e9)  # current time in nanoseconds

                        pm.send('seatControl', seat_control_msg)

                        # Mark as executed
                        executed_commands.add(csv_timestamp)

                        print(f"Executed '{command_char}' at CSV: {csv_timestamp}ms, current: {current_timestamp_ms}ms, diff: {time_diff}ms")
                        print(f"  Lateral: {lateral_cmd}, Longitudinal: {longitudinal_cmd}")

                        # Send a few more times to ensure UI catches it
                        for _ in range(29):
                            # Create a new message object for each send to avoid memory leaks
                            repeat_msg = messaging.new_message('seatControl')
                            repeat_msg.seatControl.lateralCommand = lateral_cmd
                            repeat_msg.seatControl.longitudinalCommand = longitudinal_cmd
                            repeat_msg.seatControl.timestamp = int(time.time() * 1e9)
                            pm.send('seatControl', repeat_msg)
                            time.sleep(0.01)

            # Small delay to prevent excessive CPU usage
            time.sleep(0.01)  # 10ms delay

    except KeyboardInterrupt:
        print("\nStopping trek execution...")
        print(f"Total commands executed: {len(executed_commands)}")


if __name__ == "__main__":
    main()
