# OpenPilot Log Analyzer

This directory contains tools for analyzing OpenPilot rlogs and extracting meaningful information from the message streams.

## Files

- `analyze_logs.py` - Main log analysis script that reads rlogs and prints chronological message data
- `test_analyze_logs.py` - Unit tests for the log analyzer components
- `test_script.sh` - Convenience script for testing the analyzer
- `README.md` - This documentation file

## Features

The log analyzer provides the following capabilities:

1. **Chronological Message Display**: Shows messages in time order with human-readable timestamps
2. **Multi-Topic Support**: Analyzes key message types including:
   - `modelV2` - Neural network predictions (ModelDataV2)
   - `carState` - Vehicle state information
   - `carControl` - Control commands sent to the vehicle
   - `longitudinalPlan` - Planned vehicle trajectory
   - `radarState` - Radar sensor data
   - `seatControl` - Custom seat control commands

3. **Seat Control Duration Tracking**: Special handling for seat control messages that tracks how long each command lasts

4. **Flexible Filtering**: Choose which message topics to analyze

5. **Message Limiting**: Option to limit the number of messages processed for quick analysis

## Usage

### Basic Usage

```bash
# Analyze all main topics for a route
python3 analyze_logs.py "a2a0ccea32023010|2023-01-01--12-00-00"

# Analyze a local log file
python3 analyze_logs.py /path/to/rlog.bz2

# Analyze specific topics only
python3 analyze_logs.py route_name --topics modelV2,carState,seatControl

# Limit number of messages for quick preview
python3 analyze_logs.py route_name --max-messages 100
```

### Command Line Arguments

- `log_path`: Route name (format: `dongle_id|date--time`) or path to log file
- `--topics`: Comma-separated list of message topics to analyze (default: all main topics)
- `--max-messages`: Maximum number of messages to process

### Examples

```bash
# Quick seat control analysis
python3 analyze_logs.py "route_name" --topics seatControl --max-messages 50

# Vehicle state and control analysis
python3 analyze_logs.py "route_name" --topics carState,carControl,longitudinalPlan

# Full analysis with all topics
python3 analyze_logs.py "route_name"
```

## Output Format

The analyzer prints messages chronologically with timestamps in the format:

```
[HH:MM:SS.mmm] MESSAGE_TYPE
  field1: value1
  field2: value2
  ...

[DURATION] Previous command 'COMMAND' lasted XXX.Xms
```

### Example Output

```
[14:30:45.123] CARSTATE
  vEgo: 15.50 m/s
  aEgo: 1.20 m/s²
  steeringAngleDeg: 2.5°
  blinkers: L=False, R=True

[14:30:45.125] SEATCONTROL
  command: forward
  source: accelerate
  timestamp: 14:30:45.125
  [DURATION] Previous command 'neutral' lasted 1250.5ms

[14:30:45.130] MODELV2
  frameId: 12345
  velocity: x=[15.2, 15.3, 15.4, 15.5, 15.6...] t=[0.0, 0.1, 0.2, 0.3, 0.4...]
  acceleration: x=[1.2, 1.1, 1.0, 0.9, 0.8...] t=[0.0, 0.1, 0.2, 0.3, 0.4...]
```

## Testing

Run the test suite:

```bash
# Run unit tests
python3 test_analyze_logs.py

# Run comprehensive test script
./test_script.sh
```

## Implementation Details

### SeatControlTracker Class

Tracks seat control commands and calculates durations:
- Detects command changes
- Calculates duration of previous commands
- Maintains history of command durations

### LogAnalyzer Class

Main analysis engine:
- Uses OpenPilot's LogReader for efficient log parsing
- Formats messages for human-readable display
- Handles different message types with specialized formatters
- Provides chronological message ordering

### Message Formatters

Each message type has a dedicated formatter that extracts and displays the most relevant fields:

- **ModelV2**: Frame info, velocity/acceleration predictions, position data
- **CarState**: Vehicle speed, acceleration, steering, blinkers, gear
- **CarControl**: Control state, actuator commands, HUD settings
- **LongitudinalPlan**: Speed/acceleration plans, lead vehicle status
- **RadarState**: Lead vehicle detection and tracking
- **SeatControl**: Command, source, duration tracking

## Requirements

- OpenPilot environment with cereal messaging
- Python 3.7+
- Access to OpenPilot log files (rlogs)

## Notes

- Log files can be local files (.bz2, .zst) or route names for remote logs
- The script automatically handles different log formats and compression
- Timestamps are converted from nanoseconds to human-readable format
- Large logs can be analyzed incrementally using the `--max-messages` option
