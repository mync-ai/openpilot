import pandas as pd
import sys
import tty
import time
import termios
import argparse
import os
from datetime import datetime
import cereal.messaging as messaging

subscriptions = ['carState']
# SubMaster subscribes to selected message types
sm = messaging.SubMaster(subscriptions)


def print_time():
    sm.update()
    timestamp = -1
    if sm.updated['carState']:
      timestamp = sm.logMonoTime['carState']
    return timestamp


def ns_to_ms(nanoseconds):
    """Convert nanoseconds to milliseconds"""
    return nanoseconds / 1e6


def load_existing_csv(filename):
    """Load an existing CSV file and return the timestamp and command lists"""
    try:
        if os.path.exists(filename):
            df = pd.read_csv(filename)
            if 'timestamp' in df.columns and 'command' in df.columns:
                return df['timestamp'].tolist(), df['command'].tolist()
            else:
                print(f"Warning: CSV file {filename} doesn't have required columns 'timestamp' and 'command'")
                return [], []
        else:
            print(f"File {filename} not found. Starting with empty log.")
            return [], []
    except Exception as e:
        print(f"Error loading CSV file {filename}: {e}")
        return [], []


def get_char():
    """Get a single character from stdin without pressing Enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def main():
    # Parse command line arguments
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
        print(f"Loading existing CSV file: {input_filename}")
        log_time, log_cmd = load_existing_csv(input_filename)
        if log_time and log_cmd:
            print(f"Loaded {len(log_cmd)} existing commands")
    else:
        input_filename = None
        log_time = []
        log_cmd = []

    # Define valid commands and their meanings
    valid_commands = {
        'l': 'left',
        'r': 'right',
        '[': 'hard left',
        ']': 'hard right',
        'b': 'back',
        'f': 'forward',
        ',': 'hard back',
        '.': 'hard forward',
        'n': 'neutral',
        'q': 'quit'
    }

    print("Scrubber Command Interface")
    print("=" * 30)
    print("Commands:")
    for key, description in valid_commands.items():
        if key != 'q':
            print(f"  {key} - {description}")
    print("  q - quit")

    if log_time and log_cmd:
        print(f"\nContinuing with {len(log_cmd)} existing commands")

    print("\nPress any command key (q to quit):")

    try:
        while True:
            # Update SubMaster to get latest messages

            # Get character input
            char = get_char()

            # Check if it's a valid command
            if char in valid_commands:
                if char == 'q':
                    print("\nReceived quit command. Exiting...")
                    break
                else:
                    current_time_ns = print_time()
                    if current_time_ns > 0:  # Only record if we have a valid timestamp
                        current_time_ms = ns_to_ms(current_time_ns)
                        log_time.append(current_time_ms)
                        log_cmd.append(char)
                        print(f"\nCommand: {char} ({valid_commands[char]}) at timestamp: {current_time_ms} ms")
                    else:
                        print(f"\nCommand: {char} ({valid_commands[char]}) - waiting for valid timestamp...")
            else:
                print(f"\nInvalid command: {char}. Please use valid commands.")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")

    # Convert arrays to pandas DataFrame and save to CSV
    if log_time and log_cmd:
        df = pd.DataFrame({
            'timestamp': log_time,
            'command': log_cmd
        })

        # Generate filename using first timestamp (integer milliseconds) or current datetime
        if input_filename:
            # If we loaded from an existing file, save back to the same file
            filename = input_filename
        elif log_time:
            # Use the first timestamp as integer milliseconds
            first_timestamp_ms = int(log_time[0])
            filename = f"scrubber_log_{first_timestamp_ms}.csv"
        else:
            # Fallback to datetime
            filename = f"scrubber_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        df.to_csv(filename, index=False)
        print(f"\nLog saved to {filename}")
        print(f"Total commands recorded: {len(log_cmd)}")

        # Display summary
        print("\nCommand summary:")
        command_counts = df['command'].value_counts()
        for cmd, count in command_counts.items():
            cmd_str = str(cmd)
            print(f"  {cmd_str} ({valid_commands[cmd_str]}): {count}")
    else:
        print("\nNo commands recorded.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python scrubber.py [existing_csv_file]")
        print("  existing_csv_file: Optional path to existing CSV file to continue editing")
        sys.exit(1)
    main()