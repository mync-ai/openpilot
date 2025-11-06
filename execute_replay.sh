#!/bin/bash

# Script to build openpilot and run replay with seat control services
# Ensures we're in the correct directory before executing

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

# Build openpilot
echo "🔨 Building openpilot with scons..."
echo "Command: scons -j$(nproc)"
scons -j$(nproc)

# Check if build was successful
if [[ $? -ne 0 ]]; then
    error_exit "Build failed! Please check the error messages above."
fi

echo ""
echo "✓ Build completed successfully"
echo ""

# Run replay with seat control services
echo "🎬 Starting replay with seat control services..."
echo "Command: tools/replay/replay --demo -b seatControl,seatControlConfig,seatControlConfigRequest"
echo ""

tools/replay/replay --demo -b seatControl,seatControlConfig,seatControlConfigRequest

# Check replay exit status
replay_exit_code=$?
if [[ $replay_exit_code -ne 0 ]]; then
    echo ""
    echo "⚠️  Replay exited with code $replay_exit_code"
else
    echo ""
    echo "✓ Replay completed successfully"
fi

echo ""
echo "Script finished."
