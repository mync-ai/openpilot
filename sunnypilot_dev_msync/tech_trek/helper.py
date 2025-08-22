import tty
import sys
import os
import termios

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

def ns_to_ms(nanoseconds):
    """Convert nanoseconds to milliseconds"""
    return nanoseconds / 1e6

def get_data_directory():
    """Get the path to the data directory relative to this script"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    # Create data directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def resolve_filename(filename):
    """Resolve filename to check data directory first, then current directory"""
    if filename is None:
        return None

    # If it's an absolute path, use it as-is
    if os.path.isabs(filename):
        return filename

    # First check in the data directory
    data_dir = get_data_directory()
    data_path = os.path.join(data_dir, filename)
    if os.path.exists(data_path):
        return data_path

    # Then check in current directory
    if os.path.exists(filename):
        return filename

    # If file doesn't exist anywhere, default to data directory for new files
    return data_path

def map_command_to_seat_control(command_char):
    """Map scrubber command characters to seat control commands"""
    # Command mapping from scrubber.py
    lateral_command = 'neutral'
    longitudinal_command = 'neutral'

    if command_char == 'l':  # left
        lateral_command = 'mildLeft'
    elif command_char == 'r':  # right
        lateral_command = 'mildRight'
    elif command_char == '[':  # hard left
        lateral_command = 'hardLeft'
    elif command_char == ']':  # hard right
        lateral_command = 'hardRight'
    elif command_char == 'b':  # back
        longitudinal_command = 'back'
    elif command_char == 'f':  # forward
        longitudinal_command = 'forward'
    elif command_char == 'n':  # neutral
        lateral_command = 'neutral'
        longitudinal_command = 'neutral'

    return lateral_command, longitudinal_command
