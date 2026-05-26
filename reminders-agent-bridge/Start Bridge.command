#!/bin/bash
# Double-click to start the Reminders -> Terminal bridge.
# Close this window or press Ctrl-C to stop.
cd "$(dirname "$0")"
echo "Starting Reminders agent bridge..."
exec python3 agent_inbox.py
