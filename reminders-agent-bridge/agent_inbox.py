#!/usr/bin/env python3
"""
Reminders -> Terminal bridge (the "in" direction).

Polls macOS Reminders every second. For each incomplete reminder whose title
starts with "incoming.agent:", it:
  1. activates the target terminal app
  2. pastes the message into it via clipboard + Cmd+V, then presses Return
  3. renames the reminder prefix to "agent.received:" so it isn't sent twice

The terminal is assumed to be running a CLI agent (e.g. Claude Code). The agent
replies "out" by writing a "response.agent:" reminder into the main Reminders
list (one-line AppleScript, or the included reply.sh), which a human or voice
agent reads back.

Run:   python3 agent_inbox.py
Stop:  Ctrl-C
"""

import subprocess
import time
import sys
from datetime import datetime

MATCH_PREFIX = "incoming.agent:"
DONE_PREFIX = "agent.received:"
TARGET_APP = "Terminal"
POLL_SECONDS = 1


def build_paste_text(message: str) -> str:
    """Wrap the user's message with a short footer telling the receiving agent
    how to close the loop: complete the original reminder, post a timestamped
    reply so the reader can tell which response is most recent."""
    received_title = f"{DONE_PREFIX} {message}"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"{message}\n\n"
        f'(When done: mark the reminder "{received_title}" completed, and add a '
        f'new reminder "response.agent: [{stamp}] <your reply>" to the main '
        f"Reminders list. Keep the [{stamp}] timestamp at the front so the reader "
        f"knows which response is most recent.)"
    )


# --- Step 1: pull the next unsent message and mark it received -------------
# Scans all lists. Returns the message text (after the prefix), or "" if none.
# Renames the reminder in place so it won't be picked up again.
PULL_SCRIPT = f'''
on stripPrefix(theName, thePrefix)
    return text ((count of thePrefix) + 1) thru -1 of theName
end stripPrefix

tell application "Reminders"
    repeat with l in lists
        set hits to (every reminder in l whose completed is false and name starts with "{MATCH_PREFIX}")
        if (count of hits) > 0 then
            set r to item 1 of hits
            set oldName to name of r
            set msg to my stripPrefix(oldName, "{MATCH_PREFIX}")
            set name of r to "{DONE_PREFIX}" & msg
            return msg
        end if
    end repeat
    return ""
end tell
'''


def paste_script(message: str) -> str:
    """AppleScript: set clipboard to message, activate target app, Cmd+V, Return.
    The message is passed via argv (not interpolated) to avoid quoting issues."""
    return '''
on run argv
    set theMsg to item 1 of argv
    set the clipboard to theMsg
    tell application "%s" to activate
    delay 0.4
    tell application "System Events"
        keystroke "v" using {command down}
        delay 0.2
        key code 36 -- Return
    end tell
    return "pasted"
end run
''' % TARGET_APP


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def pull_next_message() -> str:
    result = subprocess.run(
        ["osascript", "-e", PULL_SCRIPT],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        log(f"pull error: {result.stderr.strip()}")
        return ""
    return result.stdout.strip()


def paste_into_terminal(message: str) -> bool:
    result = subprocess.run(
        ["osascript", "-e", paste_script(message), message],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        log(f"paste error: {result.stderr.strip()}")
        return False
    return True


def main() -> None:
    log(f"Bridge live: Reminders {MATCH_PREFIX!r} -> {TARGET_APP} "
        f"(poll {POLL_SECONDS}s). Ctrl-C to stop.")
    while True:
        try:
            msg = pull_next_message()
            if msg:
                log(f"INCOMING: {msg}")
                if paste_into_terminal(build_paste_text(msg)):
                    log(f"-> pasted into {TARGET_APP} + Return (with protocol)")
                # small gap so we don't paste two messages on top of each other
                time.sleep(0.5)
        except subprocess.TimeoutExpired:
            log("step timed out, retrying")
        except KeyboardInterrupt:
            log("stopped.")
            sys.exit(0)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
