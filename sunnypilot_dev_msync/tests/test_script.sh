#!/bin/bash
# Quick test script for analyze_logs.py

echo "Testing analyze_logs.py script..."
echo "================================="

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZE_SCRIPT="$SCRIPT_DIR/analyze_logs.py"

echo "Script location: $ANALYZE_SCRIPT"

# Test 1: Show help
echo -e "\n1. Testing help output:"
python3 "$ANALYZE_SCRIPT" --help

# Test 2: Run unit tests
echo -e "\n2. Running unit tests:"
python3 "$SCRIPT_DIR/test_analyze_logs.py"

# Test 3: Test with a demo log path (this will likely fail, but shows usage)
echo -e "\n3. Testing with demo route (will likely fail without real log):"
python3 "$ANALYZE_SCRIPT" "demo_route|2023-01-01--12-00-00" --topics seatControl,carState --max-messages 10

echo -e "\nTest completed!"
echo "To use with real logs, replace the demo route with an actual route or log file path."
