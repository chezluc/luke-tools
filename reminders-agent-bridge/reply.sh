#!/bin/bash
# reply.sh — post a response back to the reader.
# Writes a "response.agent: [timestamp] <your text>" reminder into the main
# Reminders list. This is the "out" direction of the bridge.
#
# Usage:  ./reply.sh "your response text"
set -euo pipefail

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo 'usage: ./reply.sh "your response text"' >&2
  exit 1
fi

MSG="$*"
STAMP="$(date '+%Y-%m-%d %H:%M')"

osascript - "[$STAMP] $MSG" <<'APPLESCRIPT'
on run argv
    set body to item 1 of argv
    tell application "Reminders"
        make new reminder with properties {name:("response.agent: " & body)} at list "Reminders"
    end tell
end run
APPLESCRIPT

echo "posted: response.agent: [$STAMP] $MSG"
