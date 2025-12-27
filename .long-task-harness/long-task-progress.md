# resume-sessions - Progress Log

## Project Overview

**Started**: 2025-12-27
**Status**: In Progress
**Repository**: https://github.com/tmustier/resume-sessions

### Project Goals

Auto-titled sessions for AI coding agents. Makes `--resume` actually useful by showing what each session accomplished.

### Key Decisions

- **[D1]** Store titles in `.resume-sessions/sessions.json` in each repo (not global)
- **[D2]** Trigger on git commit (detected via tool_result hook)
- **[D3]** Use commit message as session title (simpler than LLM prompting)
- **[D4]** Format: "title1 · title2" or "first ··· last-two" if too long

---

## Current State

**Last Updated**: 2025-12-27

### What's Working
- Core session storage (load/save/update)
- Title formatting with abbreviation
- CLI commands (title, show, list, install, resume)
- Pi hook: extracts commit message, saves as title, updates tab
- Terminal tab title updates on commit
- Enhanced resume display with relative time, first message, message count
- Interactive session selector with search and keyboard navigation
- 40 tests passing

### What's Not Working
- Claude Code hook not implemented
- Hook captures full commit message body (should be first line only)

### Blocked On
- Nothing

---

## Session Log

### Session 3 | 2025-12-27 | Commits: 4c8a620..d6b8ad4

#### Metadata
- **Features**: cli-001 (completed), cli-002 (completed)
- **Files Changed**: 
  - `src/resume_sessions/__init__.py` - enhanced display + interactive selector
  - `tests/test_sessions.py` - 40 tests (up from 24)
  - `pyproject.toml` - added rich dependency
  - `README.md` - updated documentation

#### Goal
Improve CLI to match draft spec and add interactive mode

#### Accomplished
- [x] Add format_relative_time() - "2 hours ago" instead of ISO dates
- [x] Add parse_session_file() - extract first message and message count
- [x] Add format_resume_line_enhanced() - multi-line display format
- [x] Add fuzzy_filter_sessions() - search by project/message/title
- [x] Add build_session_choices() - prepare data for TUI
- [x] Add run_interactive_selector() - keyboard navigation with rich
- [x] Add --interactive/-i flag for TUI mode
- [x] Add --run flag to execute pi --resume
- [x] Add --simple flag for original single-line format
- [x] Updated README with new CLI documentation

#### Decisions
- **[D6]** Use rich library for TUI (lightweight, well-known)
- **[D7]** Enhanced format shows title, first message (truncated), and metadata
- **[D8]** Interactive mode uses termios for raw keyboard input

#### Context & Learnings
- Researched Pi's session-selector.js and claude-session-browser for inspiration
- Pi uses custom pi-tui package with React-like components
- claude-resume project stores custom session names via /rename slash command

#### Next Steps
1. Fix hook to only capture first line of commit message
2. Implement Claude Code hook
3. Consider adding numbered selection (like claude-resume: `cr 1`)

---

### Session 2 | 2025-12-27 | Commits: 5bd7633..a7ab5b8

#### Metadata
- **Features**: hook-001 (completed), terminal-001 (completed), display-001 (completed)
- **Files Changed**: 
  - `hooks/pi/resume-sessions.ts` - simplified to use commit messages
  - `src/resume_sessions/__init__.py` - added resume command
  - `tests/test_sessions.py` - 24 tests total
  - `.resume-sessions/sessions.json` - test data

#### Goal
Get Pi hook working reliably + add resume display

#### Accomplished
- [x] Tested hook in fresh Pi session
- [x] Fixed cwd extraction from `cd ~/path && git commit` commands
- [x] Simplified hook: use commit message as title instead of prompting LLM
- [x] Terminal tab title updates on each commit
- [x] Squashed 20+ debug commits into clean history
- [x] Added `resume` CLI command to display sessions with titles
- [x] Smart path resolution for Pi's encoded directory names

#### Decisions
- **[D5]** Use commit message as title instead of prompting LLM
  - Prompting had timing issues (pi.send() interrupts flow)
  - State didn't persist across Pi restarts
  - Commit messages are already good summaries

#### Surprises
- **[S1]** pi.send() injects a message but doesn't wait - subsequent text gets captured as the "response"
- **[S2]** Hook state (JS variables) resets on Pi restart - needed file persistence
- **[S3]** ctx.cwd is Pi's launch directory, not where the git command runs

#### Context & Learnings
- Pi hooks are TypeScript loaded via jiti at startup
- Hooks can write to files for debugging (/tmp/resume-sessions-debug.log)
- Need to extract cwd from `cd` prefix in bash commands
- ANSI escape `\x1b]0;TITLE\x07` updates terminal tab title

#### Next Steps
1. Implement Claude Code hook (different hook system)
2. Consider: should we also capture branch name or other context?
3. Consider: integrate with Pi's native --resume command?

---

### Session 1 | 2025-12-27 | Commits: 5bd7633

#### Metadata
- **Features**: core-001 (completed), core-002 (completed)
- **Files Changed**: 
  - `src/resume_sessions/__init__.py` - core implementation + hook installer
  - `tests/test_sessions.py` - 18 tests
  - `hooks/pi/resume-sessions.ts` - Pi hook source (initial prompting approach)
  - `pyproject.toml`, `README.md`, `AGENTS.md` - project setup

#### Goal
Initialize resume-sessions project with working Pi hook

#### Accomplished
- [x] Project structure with uv
- [x] Session storage (load/save/update to .resume-sessions/sessions.json)
- [x] Title formatting with abbreviation for long histories
- [x] CLI: title, show, list, install commands
- [x] Terminal tab title update via ANSI escape
- [x] Initial Pi hook (prompting approach - later simplified)
- [x] 18 tests passing
- [x] GitHub repo created and pushed

#### Decisions
- **[D1]** Store titles per-repo in `.resume-sessions/sessions.json`
- **[D2]** Hook detects git commit via tool_result event
- **[D3]** Hooks require Pi restart to load (loaded at startup)

#### Context & Learnings
- Pi hooks have rich event system: session, tool_call, tool_result, turn_end
- pi.send() injects messages that start new agent loops
- Hooks are TypeScript loaded via jiti - no compilation needed

#### Next Steps
1. Test hook in fresh Pi session ✅ (done in session 2)
