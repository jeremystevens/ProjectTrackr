#!/bin/bash
#
# This script runs the prune operation immediately.
# Use this to manually prune expired pastes.
#

# Get the absolute path to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3 || which python)
PRUNE_SCRIPT="$SCRIPT_DIR/prune_expired.py"

# Make sure the prune script is executable
chmod +x "$PRUNE_SCRIPT"

echo "Running paste prune operation..."
$PYTHON_PATH "$PRUNE_SCRIPT"

echo "Prune operation completed. See logs above for details."
echo "A complete log is also available in prune_expired.log"
