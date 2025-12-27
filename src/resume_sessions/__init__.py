"""LLM-generated session titles for AI coding agents."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

# Storage filename
SESSIONS_FILE = ".resume-sessions/sessions.json"


def get_sessions_path(repo_root: Optional[Path] = None) -> Path:
    """Get path to sessions.json file."""
    if repo_root is None:
        repo_root = Path.cwd()
    return repo_root / SESSIONS_FILE


def load_sessions(repo_root: Optional[Path] = None) -> dict:
    """Load sessions from JSON file."""
    path = get_sessions_path(repo_root)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_sessions(sessions: dict, repo_root: Optional[Path] = None) -> None:
    """Save sessions to JSON file."""
    path = get_sessions_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)


def get_session(session_id: str, repo_root: Optional[Path] = None) -> dict:
    """Get a session by ID, creating it if it doesn't exist."""
    sessions = load_sessions(repo_root)
    if session_id not in sessions:
        now = datetime.now(timezone.utc).isoformat()
        sessions[session_id] = {
            "titles": ["New session"],
            "created": now,
            "last_updated": now,
        }
        save_sessions(sessions, repo_root)
    return sessions[session_id]


def update_session_title(
    session_id: str, new_title: str, repo_root: Optional[Path] = None
) -> dict:
    """Update session title. Appends if different from current, otherwise just updates timestamp."""
    sessions = load_sessions(repo_root)
    now = datetime.now(timezone.utc).isoformat()

    if session_id not in sessions:
        sessions[session_id] = {
            "titles": ["New session"],
            "created": now,
            "last_updated": now,
        }

    session = sessions[session_id]
    current_title = session["titles"][-1] if session["titles"] else ""

    # Only append if title is different
    if new_title != current_title:
        session["titles"].append(new_title)

    session["last_updated"] = now
    save_sessions(sessions, repo_root)

    return session


def format_titles(titles: list[str], max_length: int = 80) -> str:
    """Format title history for display.

    - Single title: "Fix Pi discovery"
    - Multiple: "Fix Pi discovery · Add dynamic titles"
    - Many (abbreviated): "New session ··· Fix glob pattern · Add titles"
    """
    if not titles:
        return "New session"

    if len(titles) == 1:
        return titles[0]

    separator = " · "

    # Try showing all titles
    full = separator.join(titles)
    if len(full) <= max_length:
        return full

    # Abbreviate: show first and last few
    # Format: "first ··· second-to-last · last"
    first = titles[0]
    last_two = titles[-2:]

    abbreviated = f"{first} ··· {separator.join(last_two)}"
    if len(abbreviated) <= max_length:
        return abbreviated

    # Just show last two if still too long
    return separator.join(last_two)


def set_terminal_title(title: str) -> None:
    """Set terminal tab title using ANSI escape sequence."""
    # OSC 0 sets both icon name and window title
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """LLM-generated session titles for AI coding agents."""
    pass


@cli.command()
@click.argument("session_id")
@click.argument("title")
def title(session_id: str, title: str):
    """Set or update a session title.

    If the title is different from the current one, it's appended to history.
    Also updates the terminal tab title.
    """
    session = update_session_title(session_id, title)
    set_terminal_title(title)
    click.echo(f"Session titled: {format_titles(session['titles'])}")


@cli.command()
@click.argument("session_id")
def show(session_id: str):
    """Show the title history for a session."""
    session = get_session(session_id)
    click.echo(format_titles(session["titles"]))


@cli.command()
def list():
    """List all sessions with their titles."""
    sessions = load_sessions()
    if not sessions:
        click.echo("No sessions found.")
        return

    for session_id, data in sessions.items():
        titles = format_titles(data.get("titles", []))
        updated = data.get("last_updated", "unknown")[:19]
        click.echo(f"{session_id[:12]}  {updated}  {titles}")


@cli.command()
@click.argument("agent", type=click.Choice(["pi", "claude-code"]))
def install(agent: str):
    """Install hooks for an agent."""
    if agent == "pi":
        install_pi_hook()
    elif agent == "claude-code":
        install_claude_code_hook()


def install_pi_hook():
    """Install Pi agent hook."""
    hooks_dir = Path.home() / ".pi" / "agent" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "resume-sessions.ts"
    hook_content = '''import type { HookAPI } from "@mariozechner/pi-coding-agent/hooks";

export default function (pi: HookAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;

    const command = event.input.command as string;

    // Check if this is a git commit
    if (!command.includes("git commit")) return undefined;

    // Get session ID from session file path
    const sessionFile = ctx.sessionFile;
    if (!sessionFile) return undefined;

    // Extract session ID from filename
    const sessionId = sessionFile.split("/").pop()?.replace(".jsonl", "") ?? "unknown";

    // Prompt for title after commit succeeds (we'll handle this in tool_result)
    return undefined;
  });

  pi.on("tool_result", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;

    const command = event.input.command as string;
    if (!command.includes("git commit")) return undefined;

    // Only proceed if commit succeeded (exit code 0)
    if (event.isError) return undefined;

    const sessionFile = ctx.sessionFile;
    if (!sessionFile) return undefined;

    const sessionId = sessionFile.split("/").pop()?.replace(".jsonl", "") ?? "unknown";

    // Use pi.send() to ask for a title
    // The hook injects a message that the LLM will respond to
    pi.send(`[Session Title Request] Please title this session in 2-4 words. Just respond with the title, nothing else. Current working directory: ${ctx.cwd}`);

    return undefined;
  });

  // TODO: Capture the LLM's title response and save it
  // This requires intercepting the next assistant message
}
'''
    hook_path.write_text(hook_content)
    click.echo(f"Installed Pi hook: {hook_path}")
    click.echo("Note: This is a basic hook. Full implementation requires capturing LLM response.")


def install_claude_code_hook():
    """Install Claude Code hook."""
    click.echo("Claude Code hook installation not yet implemented.")
    click.echo("Claude Code uses a different hook system via ~/.claude/settings.json")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
