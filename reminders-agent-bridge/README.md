# Reminders Agent Bridge

A tiny macOS bridge that lets you **drive a terminal CLI agent (e.g. Claude Code)
through the Reminders app**. Useful as a hands-free / voice-agent inbox: a voice
assistant (or you) creates a Reminder, the bridge feeds it to your terminal, and
the agent writes its answer back as another Reminder.

Reminders is the mailbox. No server, no API keys — just AppleScript + Python
stdlib.

```
  reader / voice agent             bridge (agent_inbox.py)            CLI agent in terminal
  --------------------             -----------------------            ---------------------
  write reminder:
  "incoming.agent: do X"  ───────► sees it, renames to
                                   "agent.received: do X",
                                   pastes "do X" into terminal ──────► reads "do X", does X,
                                                                       runs ./reply.sh "done"
  read reminder:           ◄─────────────────────────────────────────  writes
  "response.agent:                                                      "response.agent:
   [time] done"                                                          [time] done"
```

## How it works

The bridge uses three title prefixes on reminders in the main **Reminders** list:

| Prefix              | Written by        | Meaning                                   |
|---------------------|-------------------|-------------------------------------------|
| `incoming.agent:`   | reader/voice agent| inbound message for the CLI agent         |
| `agent.received:`   | the bridge        | acknowledged + delivered (won't resend)   |
| `response.agent:`   | the CLI agent     | reply, prefixed with `[YYYY-MM-DD HH:MM]`  |

`agent_inbox.py` polls every second, and on each `incoming.agent:` reminder it:
1. renames the prefix to `agent.received:` (so it's delivered exactly once), then
2. sets the clipboard to the message, activates the target terminal app, and
   sends ⌘V + Return — pasting the message into the front terminal window.

The pasted text includes a short footer instructing the agent to mark the
reminder completed and post a timestamped `response.agent:` reply.

## Setup

1. **Accessibility permission** (required): System Settings → Privacy & Security
   → Accessibility → enable your terminal app. Without it, the synthetic ⌘V does
   nothing (the AppleScript still reports success).
2. That's it — it reads/writes the default **Reminders** list.

## Run

```bash
python3 agent_inbox.py
```
or double-click **`Start Bridge.command`**. Stop with Ctrl-C.

## Replying from the agent side

```bash
./reply.sh "your answer"
# -> creates: response.agent: [2026-01-01 12:00] your answer
```

## Configuration (top of `agent_inbox.py`)

| Constant        | Default            | Purpose                                  |
|-----------------|--------------------|------------------------------------------|
| `TARGET_APP`    | `"Terminal"`       | which app to paste into (e.g. `"iTerm"`) |
| `POLL_SECONDS`  | `1`                | how often to check Reminders             |
| `MATCH_PREFIX`  | `"incoming.agent:"`| inbound prefix                           |
| `DONE_PREFIX`   | `"agent.received:"`| delivered prefix                         |

## Files

- `agent_inbox.py` — the bridge (poll → rename → paste).
- `reply.sh` — helper to post a timestamped `response.agent:` reply.
- `Start Bridge.command` — double-click launcher.
- `reminders_watcher.py` — minimal variant that only renames the prefix
  (no pasting), handy for testing detection on its own.

## Notes / gotchas

- The paste goes to whatever window is frontmost when the target app activates.
- `rest` is a reserved word in AppleScript — don't use it as a variable name.
- Requires macOS (Reminders + AppleScript). Python 3.9+ stdlib only.

## License

MIT
