# resume-sessions - Progress Log

## Project Overview

**Started**: 2025-12-27
**Status**: In Progress
**Repository**: https://github.com/tmustier/resume-sessions

### Project Goals

LLM-generated session titles for AI coding agents. Makes `--resume` actually useful by showing what each session accomplished.

### Key Decisions

- **[D1]** Store titles in `.resume-sessions/sessions.json` in each repo (not global)
- **[D2]** Trigger title prompt on git commit (detected via tool_result hook)
- **[D3]** Hook saves titles directly - no CLI call needed from LLM
- **[D4]** Format: "title1 · title2" or "first ··· last-two" if too long

---

## Current State

**Last Updated**: 2025-12-27

### What's Working
- Core session storage (load/save/update)
- Title formatting with abbreviation
- CLI commands (title, show, list, install)
- Pi hook installed and ready
- 18 tests passing

### What's Not Working
- Hook needs Pi restart to load (hooks loaded at startup)
- Claude Code hook not implemented
- Agent integration (display in --resume)

### Blocked On
- Need to test hook in fresh Pi session

---

## Session Log

### Session 1 | 2025-12-27 | Commits: 5bd7633..c90494e

#### Metadata
- **Features**: core-001 (completed), core-002 (completed), hook-001 (completed)
- **Files Changed**: 
  - `src/resume_sessions/__init__.py` - core implementation + hook installer
  - `tests/test_sessions.py` - 18 tests
  - `hooks/pi/resume-sessions.ts` - Pi hook source
  - `pyproject.toml`, `README.md`, `AGENTS.md` - project setup

#### Goal
Initialize resume-sessions project with working Pi hook

#### Accomplished
- [x] Project structure with uv
- [x] Session storage (load/save/update to .resume-sessions/sessions.json)
- [x] Title formatting with abbreviation for long histories
- [x] CLI: title, show, list, install commands
- [x] Terminal tab title update via ANSI escape
- [x] Pi hook that:
  - Detects git commit via tool_result
  - Prompts LLM for 2-4 word title via pi.send()
  - Captures response and extracts title
  - Saves directly to sessions.json (no CLI needed)
  - Updates terminal tab title
- [x] 18 tests passing
- [x] GitHub repo created and pushed
- [ ] Test hook in fresh Pi session (requires restart)

#### Decisions
- **[D1]** Hook captures LLM response directly instead of requiring CLI call
- **[D2]** Title extraction uses heuristics (2-6 words, skip explanatory text)
- **[D3]** Hooks require Pi restart to load (loaded at startup)

#### Context & Learnings
- Pi hooks have rich event system: session, tool_call, tool_result, turn_end
- pi.send() injects messages that start new agent loops
- Can capture LLM response in subsequent turn_end via event.message
- Hooks are TypeScript loaded via jiti - no compilation needed

#### Next Steps
1. Test hook in fresh Pi session
2. Implement Claude Code hook (different hook system via settings.json)
3. PR to Pi to display titles in --resume

