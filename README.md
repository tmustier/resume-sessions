# resume-sessions

LLM-generated session titles for AI coding agents. Makes `--resume` actually useful.

## The Problem

When resuming a session, you see:
```
Ok so this does not work. Please could you review and try to make it work? It was forked from another ski...
8 minutes ago · 174 messages
```

This tells you nothing about what the session accomplished.

## The Solution

With resume-sessions, you see:
```
Fix Pi discovery · Add dynamic titles
Ok so this does not work. Please could you review and try to make it work? It was forked from another ski...
8 minutes ago · 174 messages · 10 commits
```

The LLM titles the session in 2-4 words at each commit. If the focus changes, a new title is added.

## How It Works

1. **Pre-commit hook** prompts the LLM: "Title this session in 2-4 words"
2. Titles are stored in `.resume-sessions/sessions.json` in the repo
3. When resuming, the agent reads and displays the title history

## Supported Agents

- [x] Pi (`~/.pi/agent/hooks/`)
- [ ] Claude Code (`~/.claude/settings.json` hooks)
- [ ] Codex
- [ ] Droid

## Installation

```bash
# Install the CLI
uv tool install resume-sessions

# Install hooks for your agent
resume-sessions install pi
resume-sessions install claude-code
```

## Storage Format

`.resume-sessions/sessions.json`:
```json
{
  "session_id_abc123": {
    "titles": ["New session", "Fix Pi discovery", "Add dynamic titles"],
    "created": "2025-12-26T23:00:00Z",
    "last_updated": "2025-12-27T00:30:00Z"
  }
}
```

## Display Format

Single title:
```
Fix Pi discovery
```

Multiple titles (focus changed):
```
Fix Pi discovery · Add dynamic titles
```

Many titles (abbreviated):
```
New session ··· Fix glob pattern · Add transcript titles
```

## Terminal Tab Title

On each title update, the terminal tab is renamed to the current title using ANSI escape sequences.

## Development

```bash
cd ~/resume-sessions
uv run pytest
uv run resume-sessions --help
```

## License

MIT
