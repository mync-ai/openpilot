#!/bin/bash

# Script to execute openpilot UI
# Ensures we're in the correct directory and activates virtual environment

# Function to display error message and exit
error_exit() {
    echo "Error: $1" >&2
    exit 1
}

# Check if we're in the openpilot directory
if [[ ! -d "selfdrive" ]] || [[ ! -f "SConstruct" ]]; then
    error_exit "This script must be run from the openpilot/ directory. Current directory: $(pwd)"
fi

# Verify we're actually in a directory named 'openpilot'
current_dir=$(basename "$(pwd)")
if [[ "$current_dir" != "openpilot" ]]; then
    echo "Warning: Current directory name is '$current_dir', expected 'openpilot'"
    echo "Continuing anyway since openpilot files are present..."
fi

echo "✓ Confirmed we're in the openpilot directory"
echo "Current directory: $(pwd)"
echo ""

# Check if virtual environment exists
if [[ ! -d ".venv" ]]; then
    error_exit "Virtual environment not found. Please ensure .venv directory exists."
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Check if activation was successful
if [[ -z "$VIRTUAL_ENV" ]]; then
    error_exit "Failed to activate virtual environment"
fi

echo "✓ Virtual environment activated: $VIRTUAL_ENV"
echo ""

# Check if UI binary exists
if [[ ! -f "selfdrive/ui/ui" ]]; then
    error_exit "UI binary not found at selfdrive/ui/ui. Please build openpilot first with 'scons -j$(nproc)'"
fi

echo "🖥️  Starting openpilot UI..."
echo "Command: selfdrive/ui/ui"
echo ""

# Execute the UI
selfdrive/ui/ui

# Check UI exit status
ui_exit_code=$?
if [[ $ui_exit_code -ne 0 ]]; then
    echo ""
    echo "⚠️  UI exited with code $ui_exit_code"
else
    echo ""
    echo "✓ UI exited successfully"
fi

echo ""
echo "Script finished."