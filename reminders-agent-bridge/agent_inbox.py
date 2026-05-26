#!/usr/bin/env python3
"""
Reminders -> Terminal bridge (the "in" direction).

Polls macOS Reminders every second, finds a new incoming message, and:
  1. tags the reminder "agent.received:" so it isn't sent twice
  2. activates the target terminal app
  3. pastes the message into it via clipboard + Cmd+V, then presses Return

Two modes (set REQUIRE_PREFIX below):

  REQUIRE_PREFIX = True  (default, safe)
      A message is any reminder whose title starts with "incoming.agent:".
      Use this if you also use Reminders for normal to-dos -- only tagged
      reminders are picked up.

  REQUIRE_PREFIX = False (no prefix)
      A message is ANY new reminder in INBOX_LIST that the bridge didn't tag
      itself. Just type/speak the message -- no prefix to remember. Use this
      only if you dedicate the list to the bridge.

The terminal is assumed to be running a CLI agent (e.g. Claude Code). The agent
replies "out" by writing a "response.agent:" reminder into the list (one-line
AppleScript, or the included reply.sh), which a human or voice agent reads back.

Run:   python3 agent_inbox.py
Stop:  Ctrl-C
"""

import subprocess
import time
import sys
from datetime import datetime

# --- config ----------------------------------------------------------------
REQUIRE_PREFIX = True              # True = need "incoming.agent:"; False = any reminder
MATCH_PREFIX = "incoming.agent:"   # the incoming prefix (used when REQUIRE_PREFIX)
DONE_PREFIX = "agent.received:"    # bridge tags delivered messages with this
RESPONSE_PREFIX = "response.agent:"  # the agent's own replies -- never re-send
INBOX_LIST = "Reminders"           # which Reminders list to watch
TARGET_APP = "Terminal"            # which app to paste into (e.g. "iTerm")
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


# --- Step 1: build the AppleScript that pulls the next unsent message -------
# Returns the message text and tags the reminder so it won't be picked up again.
def _build_pull_script() -> str:
    if REQUIRE_PREFIX:
        # Watch INBOX_LIST for titles starting with MATCH_PREFIX; strip the
        # prefix from the returned text and re-tag with DONE_PREFIX.
        return f'''
        on stripPrefix(theName, thePrefix)
            return text ((count of thePrefix) + 1) thru -1 of theName
        end stripPrefix

        tell application "Reminders"
            set theList to list "{INBOX_LIST}"
            repeat with r in (every reminder in theList whose completed is false and name starts with "{MATCH_PREFIX}")
                set oldName to name of r
                set msg to my stripPrefix(oldName, "{MATCH_PREFIX}")
                set name of r to "{DONE_PREFIX} " & msg
                return msg
            end repeat
            return ""
        end tell
        '''
    # No-prefix mode: a message is any reminder in INBOX_LIST that isn't already
    # one of the bridge's own tagged items (agent.received: / response.agent:).
    return f'''
    tell application "Reminders"
        set theList to list "{INBOX_LIST}"
        repeat with r in (every reminder in theList whose completed is false)
            set nm to name of r
            if (nm does not start with "{DONE_PREFIX}") and (nm does not start with "{RESPONSE_PREFIX}") then
                set name of r to "{DONE_PREFIX} " & nm
                return nm
            end if
        end repeat
        return ""
    end tell
    '''


PULL_SCRIPT = _build_pull_script()


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
    mode = f"prefix {MATCH_PREFIX!r}" if REQUIRE_PREFIX else "any new reminder (no prefix)"
    log(f"Bridge live: {INBOX_LIST!r} list [{mode}] -> {TARGET_APP} "
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
