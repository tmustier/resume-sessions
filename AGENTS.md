# resume-sessions Development

Uses uv. Run tests like this:

    uv run pytest

Run the development version of the tool like this:

    uv run resume-sessions --help

Always practice TDD: write a failing test, watch it fail, then make it pass.

Commit early and often. Commits should bundle the test, implementation, and documentation changes together.

Run Black to format code before you commit:

    uv run black .

## Multi-Session Development

This project uses long-task-harness for session continuity.
At session start or after context reset, invoke the skill at:
/Users/thomasmustier/.claude/skills/long-task-harness
