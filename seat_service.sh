#!/bin/bash

# Seat Control Configuration Script
# This script activates the virtual environment and launches the seat control service

# Activate the virtual environment
source .venv/bin/activate

# Launch the interactive seat control CLI
python sunnypilot_dev_msync/msync_src/seat_control_service_enhanced.py
