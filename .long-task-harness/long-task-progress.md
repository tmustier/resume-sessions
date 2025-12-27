# resume-sessions - Progress Log

## Project Overview

**Started**: 2025-12-27
**Status**: In Progress
**Repository**: https://github.com/tmustier/resume-sessions

### Project Goals

LLM-generated session titles for AI coding agents. Makes `--resume` actually useful by showing what each session accomplished.

### Key Decisions

- **[D1]** Store titles in `.resume-sessions/sessions.json` in each repo (not global)
- **[D2]** Trigger title prompt on pre-commit hook (natural checkpoint)
- **[D3]** Accumulate title history (show evolution of session focus)
- **[D4]** Format: "title1 · title2" or "first ··· last-two" if too long

---

## Current State

**Last Updated**: 2025-12-27

### What's Working
- Core session storage (load/save/update)
- Title formatting with abbreviation
- CLI commands (title, show, list, install)
- 18 tests passing

### What's Not Working
- Pi hook needs LLM response capture mechanism
- Claude Code hook not implemented
- Agent integration (display in --resume)

### Blocked On
- Need to figure out how to capture LLM response to title prompt in Pi hook

---

## Session Log

### Session 1 | 2025-12-27 | Commits: pending

#### Metadata
- **Features**: core-001 (completed), core-002 (completed), hook-001 (started)
- **Files Changed**: 
  - `src/resume_sessions/__init__.py` - core implementation
  - `tests/test_sessions.py` - 18 tests
  - `pyproject.toml`, `README.md`, `AGENTS.md` - project setup

#### Goal
Initialize resume-sessions project with core functionality

#### Accomplished
- [x] Project structure with uv
- [x] Session storage (load/save/update to .resume-sessions/sessions.json)
- [x] Title formatting with abbreviation for long histories
- [x] CLI: title, show, list, install commands
- [x] Terminal tab title update (set_terminal_title)
- [x] Basic Pi hook structure (needs LLM response capture)
- [x] 18 tests passing
- [ ] Figure out LLM response capture for hooks

#### Decisions
- **[D1]** Using .resume-sessions/sessions.json per-repo storage
- **[D2]** Pi hook uses tool_result event after git commit succeeds
- **[D3]** pi.send() can inject title request, but capturing response is tricky

#### Context & Learnings
- Pi hooks have rich event system with tool_call/tool_result events
- Can detect git commit via bash tool with command matching
- pi.send() injects messages but there's no direct way to capture the response
- May need a different approach: perhaps use a custom tool or file-based handoff

#### Next Steps
1. Design LLM response capture mechanism for Pi hook
2. Test hook end-to-end with real Pi session
3. Create GitHub repo and push

