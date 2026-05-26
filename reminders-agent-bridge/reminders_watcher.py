#!/usr/bin/env python3
"""
Reminders watcher.

Polls the macOS Reminders app every second for incomplete reminders whose
title starts with "incoming.agent:". When found, rewrites the prefix to
"agent.received:" so it won't match again.

Run:   python3 reminders_watcher.py
Stop:  Ctrl-C
"""

import subprocess
import time
import sys
from datetime import datetime

MATCH_PREFIX = "incoming.agent:"
NEW_PREFIX = "agent.received:"
POLL_SECONDS = 1

# AppleScript: find incomplete reminders whose name starts with MATCH_PREFIX,
# rewrite the prefix in place, and print each old title that was changed.
RENAME_SCRIPT = f'''
on replacePrefix(theName, oldPrefix, newPrefix)
    if theName starts with oldPrefix then
        set tailText to text ((count of oldPrefix) + 1) thru -1 of theName
        return newPrefix & tailText
    else
        return theName
    end if
end replacePrefix

tell application "Reminders"
    set changed to {{}}
    set matches to (every reminder whose completed is false and name starts with "{MATCH_PREFIX}")
    repeat with r in matches
        set oldName to name of r
        set name of r to my replacePrefix(oldName, "{MATCH_PREFIX}", "{NEW_PREFIX}")
        set end of changed to oldName
    end repeat
    set AppleScript's text item delimiters to linefeed
    return changed as text
end tell
'''


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def poll_once() -> list[str]:
    """Run the AppleScript; return list of original titles that were rewritten."""
    result = subprocess.run(
        ["osascript", "-e", RENAME_SCRIPT],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        log(f"osascript error: {result.stderr.strip()}")
        return []
    out = result.stdout.strip()
    return [line for line in out.splitlines() if line] if out else []


def main() -> None:
    log(f"Watching Reminders for titles starting with {MATCH_PREFIX!r} "
        f"(polling every {POLL_SECONDS}s). Ctrl-C to stop.")
    while True:
        try:
            changed = poll_once()
            for old in changed:
                new = NEW_PREFIX + old[len(MATCH_PREFIX):]
                log(f"MATCH  {old!r}  ->  {new!r}")
        except subprocess.TimeoutExpired:
            log("poll timed out, retrying")
        except KeyboardInterrupt:
            log("stopped.")
            sys.exit(0)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
