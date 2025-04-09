#!/bin/bash
#
# This script sets up a cron job to prune expired pastes every 10 minutes
#

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3 || which python)
PRUNE_SCRIPT="$PROJECT_DIR/prune_expired.py"

# Make sure the prune script is executable
chmod +x "$PRUNE_SCRIPT"

# Create a temporary file for the crontab
TEMP_CRON=$(mktemp)

# Get the existing crontab
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "# New crontab" > "$TEMP_CRON"

# Check if the cron job already exists
if grep -q "$PRUNE_SCRIPT" "$TEMP_CRON"; then
    echo "Cron job already exists. No changes made."
    rm "$TEMP_CRON"
    exit 0
fi

# Add the new cron job
echo "# Run the paste pruner every 10 minutes" >> "$TEMP_CRON"
echo "*/10 * * * * cd $PROJECT_DIR && $PYTHON_PATH $PRUNE_SCRIPT >> $PROJECT_DIR/prune_expired.log 2>&1" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"
RET=$?

# Clean up
rm "$TEMP_CRON"

if [ $RET -eq 0 ]; then
    echo "Successfully installed cron job to prune expired pastes every 10 minutes."
    echo "To view your crontab, run: crontab -l"
    echo "To edit your crontab, run: crontab -e"
else
    echo "Failed to install cron job. Please check your permissions."
    exit 1
fi

exit 0
