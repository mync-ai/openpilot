#!/usr/bin/env python3
"""
Trek Runner Module

This module loads a CSV file containing timestamps and commands, then publishes
seat control commands when the current timestamp matches entries in the CSV.
"""
from helper import *
import sys
import time
import pandas as pd
import os
from cereal import messaging
import asyncio


class TrekRunner:
    """Main trek runner class that handles both seat control and BLE messaging"""

    def __init__(self, csv_filename):
        self.csv_filename = csv_filename
        self.commands_dict = None
        self.executed_commands = set()
        self.pm = None
        self.sm = None
        self.ble_client = None
        self.ble_cmds = {'l':'l', 'r':'r', '[':'L', ']':'R', 'f':'A', 'b':'B'}

    async def setup(self):
        """Set up messaging and BLE connection"""
        # Load CSV commands
        self.commands_dict = self.load_csv_commands(self.csv_filename)

        # Set up openpilot messaging
        print("Setting up messaging...")
        self.pm = messaging.PubMaster(['seatControl'])
        self.sm = messaging.SubMaster(['carState'])

        # Set up BLE connection
        print("Connecting to BLE device...")
        try:
            self.ble_client = await connect_ble("HapticPillow")
            print("BLE connection established")
        except Exception as e:
            print(f"BLE connection failed: {e}")
            print("Continuing without BLE...")
            self.ble_client = None

    async def cleanup(self):
        """Clean up connections"""
        if self.ble_client:
            try:
                await self.ble_client.disconnect()
                print("BLE disconnected")
            except Exception as e:
                print(f"BLE disconnect error: {e}")

    def load_csv_commands(self, filename):
        """Load commands from CSV file and return as a dictionary with timestamps as keys"""
        try:
            # Check if file exists in data directory first
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, 'data')

            # Try data directory first, then current directory
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
                timestamp_ms = int(row['timestamp'])
                command = row['command']
                commands_dict[timestamp_ms] = command

            print(f"Loaded {len(commands_dict)} commands from CSV")
            return commands_dict

        except Exception as e:
            print(f"Error loading CSV file {filename}: {e}")
            sys.exit(1)

    def get_current_timestamp_ms(self):
        """Get current timestamp in milliseconds from carState"""
        self.sm.update()
        if self.sm.updated['carState']:
            timestamp_ns = self.sm.logMonoTime['carState']
            return ns_to_ms(timestamp_ns)
        return -1

    async def send_command(self, command_char, lateral_cmd, longitudinal_cmd):
        """Send command to both seat control and BLE device"""
        # Send to openpilot seat control
        seat_control_msg = messaging.new_message('seatControl')
        seat_control_msg.seatControl.lateralCommand = lateral_cmd
        seat_control_msg.seatControl.longitudinalCommand = longitudinal_cmd
        seat_control_msg.seatControl.timestamp = int(time.time() * 1e9)

        self.pm.send('seatControl', seat_control_msg)

        # Send to BLE device (if connected)
        if self.ble_client:
            try:
                ble_char = self.ble_cmds.get(command_char, 'n/a')
                await send_ble_command(self.ble_client, ble_char)
            except Exception as e:
                print(f"BLE send error: {e}")

        # Send multiple times to ensure UI catches it
        for _ in range(29):
            repeat_msg = messaging.new_message('seatControl')
            repeat_msg.seatControl.lateralCommand = lateral_cmd
            repeat_msg.seatControl.longitudinalCommand = longitudinal_cmd
            repeat_msg.seatControl.timestamp = int(time.time() * 1e9)
            self.pm.send('seatControl', repeat_msg)
            await asyncio.sleep(0.001)  # 1ms delay, non-blocking

    async def run(self):
        """Main execution loop"""
        await self.setup()

        print("Starting trek execution...")
        print("Press Ctrl+C to stop")

        # Convert command dict to sorted list for range searching
        sorted_timestamps = sorted(self.commands_dict.keys())
        TOLERANCE_MS = 20  # 20ms tolerance

        try:
            while True:
                # Get current timestamp
                current_timestamp_ms = self.get_current_timestamp_ms()

                if current_timestamp_ms > 0:
                    # Find commands within tolerance window
                    for csv_timestamp in sorted_timestamps:
                        if csv_timestamp in self.executed_commands:
                            continue

                        # Check if current timestamp is within tolerance of CSV timestamp
                        time_diff = abs(current_timestamp_ms - csv_timestamp)
                        if time_diff <= TOLERANCE_MS:
                            command_char = self.commands_dict[csv_timestamp]

                            # Map command to seat control
                            lateral_cmd, longitudinal_cmd = map_command_to_seat_control(command_char)

                            # Send command to both systems
                            await self.send_command(command_char, lateral_cmd, longitudinal_cmd)

                            # Mark as executed
                            self.executed_commands.add(csv_timestamp)

                            print(f"Executed '{command_char}' at CSV: {csv_timestamp}ms, "
                                  f"current: {current_timestamp_ms}ms, diff: {time_diff}ms")
                            print(f"  Lateral: {lateral_cmd}, Longitudinal: {longitudinal_cmd}")

                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.01)  # 10ms delay, non-blocking

        except KeyboardInterrupt:
            print("\nStopping trek execution...")
            print(f"Total commands executed: {len(self.executed_commands)}")
        finally:
            await self.cleanup()


async def main():
    """Async main function"""
    if len(sys.argv) != 2:
        print("Usage: python run_trek.py <csv_file>")
        print("  csv_file: CSV file containing timestamps and commands")
        sys.exit(1)

    csv_filename = sys.argv[1]
    runner = TrekRunner(csv_filename)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
