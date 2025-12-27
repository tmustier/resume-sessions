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
  Ok so this does not work. Please could you review...
  8 minutes ago · 174 messages · ~/my-project
```

The LLM titles the session based on commit messages. If the focus changes, a new title is added.

## Quick Start

```bash
# Install the CLI
uv tool install resume-sessions

# Install hooks for your agent
resume-sessions install pi

# View recent sessions
resume-sessions resume

# Interactive session picker
resume-sessions resume -i

# Select and resume a session
resume-sessions resume --run
```

## CLI Usage

```bash
# Show last 10 sessions with titles, first message, and metadata
resume-sessions resume

# Show last 5 sessions
resume-sessions resume -n 5

# Filter by project name (fuzzy match)
resume-sessions resume -p dashboard

# Simple one-line format
resume-sessions resume --simple

# Interactive TUI with search
resume-sessions resume -i

# Select a session and run `pi --resume`
resume-sessions resume --run
```

### Interactive Mode

The interactive mode (`-i` or `--run`) provides:
- **↑↓** Navigate sessions
- **/** Search by project, title, or message content
- **Enter** Select session
- **Esc** Clear search
- **q** Quit

## How It Works

1. **Post-commit hook** captures the commit message as the session title
2. Titles are stored in `.resume-sessions/sessions.json` in each repo
3. The `resume` command discovers sessions and displays them with titles

## Supported Agents

- [x] Pi (`~/.pi/agent/hooks/`)
- [ ] Claude Code (`~/.claude/settings.json` hooks)
- [ ] Codex
- [ ] Droid

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

**Enhanced (default):**
```
Fix Pi discovery · Add dynamic titles
  Ok so this does not work. Please could you review...
  8 minutes ago · 174 messages · ~/my-project
```

**Simple (`--simple`):**
```
2025-12-27 01:28  ~/my-project                    Fix Pi discovery · Add dynamic titles
```

## Terminal Tab Title

On each commit, the terminal tab is renamed to the commit message (first line) using ANSI escape sequences.

## Development

```bash
cd ~/resume-sessions
uv run pytest           # Run tests
uv run black .          # Format code
uv run resume-sessions --help
```

## License

MIT





