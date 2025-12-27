"""LLM-generated session titles for AI coding agents."""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import click


def format_relative_time(dt: datetime) -> str:
    """Format a datetime as relative time (e.g., '2 hours ago').

    Args:
        dt: datetime object (should be timezone-aware UTC)

    Returns:
        Human-readable relative time string
    """
    now = datetime.now(timezone.utc)

    # Handle naive datetimes by assuming UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"

    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = int(seconds / 3600)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = int(seconds / 86400)
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    weeks = int(days / 7)
    if weeks < 5:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    # For older dates, show the actual date
    return dt.strftime("%Y-%m-%d")


def parse_session_file(path: Path) -> dict:
    """Parse a Pi session JSONL file to extract metadata.

    Args:
        path: Path to the .jsonl session file

    Returns:
        dict with:
          - first_message: First user message text
          - message_count: Total number of messages
          - modified: File modification time as datetime
    """
    first_message = ""
    message_count = 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Count messages
                    if entry.get("type") == "message":
                        message_count += 1
                        msg = entry.get("message", {})
                        # Capture first user message
                        if not first_message and msg.get("role") == "user":
                            content = msg.get("content", [])
                            for block in content:
                                if block.get("type") == "text":
                                    first_message = block.get("text", "")
                                    break
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        pass

    # Get file modification time
    try:
        mtime = path.stat().st_mtime
        modified = datetime.fromtimestamp(mtime, tz=timezone.utc)
    except (IOError, OSError):
        modified = datetime.now(timezone.utc)

    return {
        "first_message": first_message,
        "message_count": message_count,
        "modified": modified,
    }


def format_resume_line_enhanced(session_info: dict, titles: Optional[list[str]]) -> str:
    """Format a session for enhanced resume display.

    Shows:
      Line 1: Title (or project path if no title)
      Line 2: First message (truncated) + metadata

    Args:
        session_info: dict with id, project, path, modified, first_message, message_count
        titles: list of titles or None if no title data

    Returns:
        Multi-line formatted string
    """
    # Format title
    if titles:
        title_str = format_titles(titles, max_length=60)
    else:
        title_str = project_name_to_path(session_info.get("project", ""))

    # Format relative time
    modified = session_info.get("modified")
    if isinstance(modified, datetime):
        time_str = format_relative_time(modified)
    else:
        time_str = "unknown"

    # Format message count
    count = session_info.get("message_count", 0)
    count_str = f"{count} message{'s' if count != 1 else ''}"

    # Format first message (truncated)
    first_msg = session_info.get("first_message", "")
    # Normalize whitespace
    first_msg = " ".join(first_msg.split())
    max_msg_len = 70
    if len(first_msg) > max_msg_len:
        first_msg = first_msg[: max_msg_len - 3] + "..."

    # Build output
    lines = []
    lines.append(click.style(title_str, bold=True))

    # Second line: first message (dimmed) if available
    if first_msg:
        lines.append(click.style(f"  {first_msg}", dim=True))

    # Third line: metadata
    project_path = project_name_to_path(session_info.get("project", ""))
    if len(project_path) > 25:
        project_path = "..." + project_path[-22:]
    meta = f"  {time_str} · {count_str} · {project_path}"
    lines.append(click.style(meta, dim=True))

    return "\n".join(lines)


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


# --- Pi Session Discovery ---


def get_pi_sessions_dir() -> Path:
    """Get the Pi agent sessions directory."""
    return Path.home() / ".pi" / "agent" / "sessions"


def find_pi_sessions(sessions_dir: Optional[Path] = None) -> list[dict]:
    """Find all Pi agent session files.

    Returns a list of dicts with:
      - id: session ID (filename without .jsonl)
      - project: project directory name
      - path: full path to session file
    """
    if sessions_dir is None:
        sessions_dir = get_pi_sessions_dir()

    if not sessions_dir.exists():
        return []

    sessions = []
    for session_file in sessions_dir.glob("**/*.jsonl"):
        session_id = session_file.stem
        project = session_file.parent.name
        sessions.append(
            {
                "id": session_id,
                "project": project,
                "path": session_file,
            }
        )

    # Sort by ID (which starts with timestamp) descending
    sessions.sort(key=lambda s: s["id"], reverse=True)
    return sessions


def project_name_to_path(project_dir_name: str) -> str:
    """Convert Pi project directory name to readable path.

    Pi encodes paths by replacing / with -, so /Users/foo/my-project becomes
    Users-foo-my-project. This is lossy (can't distinguish - in names from /).

    We try to find the actual directory by checking if paths exist.
    """
    # Remove leading/trailing --
    encoded = project_dir_name.strip("-")

    # Try to find the actual path by testing candidates
    # Start from home directory and work down
    home = Path.home()
    home_str = str(home)[1:]  # Remove leading / to match encoded format

    if encoded.startswith(home_str.replace("/", "-")):
        # Path is under home directory
        remaining = encoded[len(home_str.replace("/", "-")) :]
        if remaining.startswith("-"):
            remaining = remaining[1:]

        # Try to resolve the remaining path
        # Split on - and try to find actual directories
        if remaining:
            resolved = _resolve_encoded_path(home, remaining)
            if resolved:
                return "~/" + str(resolved.relative_to(home))
        return "~"

    # Fallback: just replace - with /
    return "/" + encoded.replace("-", "/")


def _resolve_encoded_path(base: Path, encoded: str) -> Optional[Path]:
    """Try to resolve an encoded path segment to an actual directory.

    Uses greedy matching: tries longest possible directory names first.
    """
    if not encoded:
        return base

    parts = encoded.split("-")

    # Try increasingly longer prefixes
    for i in range(len(parts), 0, -1):
        candidate_name = "-".join(parts[:i])
        candidate_path = base / candidate_name

        if candidate_path.exists():
            remaining = "-".join(parts[i:])
            if not remaining:
                return candidate_path
            result = _resolve_encoded_path(candidate_path, remaining)
            if result:
                return result

    return None


def format_resume_line(session_info: dict, titles: Optional[list[str]]) -> str:
    """Format a single session for resume display.

    Args:
        session_info: dict with id, project, path
        titles: list of titles or None if no title data

    Returns:
        Formatted line like: "2025-01-15 10:30  ~/myproject  Fix bug · Add tests"
    """
    session_id = session_info["id"]
    project = session_info["project"]

    # Extract date/time from session ID (format: 2025-01-15T10-30-00_uuid)
    try:
        timestamp_part = session_id.split("_")[0]
        date_str = timestamp_part[:10]  # 2025-01-15
        time_str = timestamp_part[11:16].replace("-", ":")  # 10:30
        datetime_str = f"{date_str} {time_str}"
    except (IndexError, ValueError):
        datetime_str = session_id[:16]

    # Convert project name to readable path
    project_path = project_name_to_path(project)
    # Truncate long project paths
    if len(project_path) > 30:
        project_path = "..." + project_path[-27:]

    # Format titles
    if titles:
        title_str = format_titles(titles, max_length=50)
    else:
        title_str = "(no title)"

    return f"{datetime_str}  {project_path:<30}  {title_str}"


def load_titles_for_session(session_id: str, project_path: str) -> Optional[list[str]]:
    """Load titles for a session from the project's .resume-sessions/sessions.json.

    Args:
        session_id: The session ID
        project_path: Path to the project directory (e.g., ~/myproject)

    Returns:
        List of titles or None if not found
    """
    # Expand ~ and resolve path
    project_dir = Path(project_path).expanduser()
    sessions_file = project_dir / ".resume-sessions" / "sessions.json"

    if not sessions_file.exists():
        return None

    try:
        with open(sessions_file, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        if session_id in sessions:
            return sessions[session_id].get("titles", [])
    except (json.JSONDecodeError, IOError):
        pass

    return None


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
@click.option("-n", "--limit", default=10, help="Number of sessions to show")
@click.option(
    "-p", "--project", default=None, help="Filter by project path (fuzzy match)"
)
@click.option("--simple", is_flag=True, help="Use simple single-line format")
def resume(limit: int, project: Optional[str], simple: bool):
    """Show recent Pi sessions with their titles.

    Discovers sessions from ~/.pi/agent/sessions/ and matches them
    with titles from each project's .resume-sessions/sessions.json

    Examples:

        resume-sessions resume              # Show last 10 sessions

        resume-sessions resume -n 5         # Show last 5 sessions

        resume-sessions resume -p dashboard # Filter by project name
    """
    sessions = find_pi_sessions()

    if not sessions:
        click.echo("No Pi sessions found.")
        return

    # Filter by project if specified (fuzzy match)
    if project:
        project_lower = project.lower()
        sessions = [
            s
            for s in sessions
            if project_lower in s["project"].lower()
            or project_lower in project_name_to_path(s["project"]).lower()
        ]

    # Limit results
    sessions = sessions[:limit]

    if not sessions:
        click.echo("No matching sessions found.")
        return

    # Enrich sessions with parsed data
    for session_info in sessions:
        parsed = parse_session_file(session_info["path"])
        session_info.update(parsed)

    for i, session_info in enumerate(sessions):
        # Convert project dir name to path for title lookup
        project_path = project_name_to_path(session_info["project"])
        titles = load_titles_for_session(session_info["id"], project_path)

        if simple:
            line = format_resume_line(session_info, titles)
            click.echo(line)
        else:
            line = format_resume_line_enhanced(session_info, titles)
            click.echo(line)
            if i < len(sessions) - 1:
                click.echo()  # Blank line between sessions


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

    # Read the hook from package data or use inline version
    hook_content = """/**
 * Pi agent hook for resume-sessions.
 * After a successful git commit, prompts the LLM to title the session.
 * Captures the response and saves directly to .resume-sessions/sessions.json
 */
import type { HookAPI } from "@mariozechner/pi-coding-agent/hooks";
import * as fs from "node:fs";
import * as path from "node:path";

interface Session {
  titles: string[];
  created: string;
  last_updated: string;
}

interface Sessions {
  [key: string]: Session;
}

let awaitingTitleResponse = false;
let currentSessionId: string | null = null;
let currentCwd: string | null = null;

function loadSessions(cwd: string): Sessions {
  const sessionsFile = path.join(cwd, ".resume-sessions", "sessions.json");
  try {
    if (fs.existsSync(sessionsFile)) {
      return JSON.parse(fs.readFileSync(sessionsFile, "utf-8"));
    }
  } catch {}
  return {};
}

function saveSessions(cwd: string, sessions: Sessions): void {
  const sessionsDir = path.join(cwd, ".resume-sessions");
  const sessionsFile = path.join(sessionsDir, "sessions.json");
  
  if (!fs.existsSync(sessionsDir)) {
    fs.mkdirSync(sessionsDir, { recursive: true });
  }
  fs.writeFileSync(sessionsFile, JSON.stringify(sessions, null, 2));
}

function getCurrentTitle(sessions: Sessions, sessionId: string): string {
  const session = sessions[sessionId];
  if (session?.titles?.length > 0) {
    return session.titles[session.titles.length - 1];
  }
  return "New session";
}

function updateTitle(cwd: string, sessionId: string, newTitle: string): void {
  const sessions = loadSessions(cwd);
  const now = new Date().toISOString();
  
  if (!sessions[sessionId]) {
    sessions[sessionId] = {
      titles: ["New session"],
      created: now,
      last_updated: now,
    };
  }
  
  const session = sessions[sessionId];
  const currentTitle = session.titles[session.titles.length - 1];
  
  // Only append if different
  if (newTitle !== currentTitle) {
    session.titles.push(newTitle);
  }
  session.last_updated = now;
  
  saveSessions(cwd, sessions);
  
  // Update terminal tab title
  process.stdout.write(`\\x1b]0;${newTitle}\\x07`);
}

function extractTitle(text: string): string | null {
  const lines = text.trim().split("\\n");
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.length > 50) continue;
    if (trimmed.toLowerCase().includes("title unchanged")) return null;
    if (trimmed.toLowerCase().includes("current title")) continue;
    if (trimmed.startsWith("[") || trimmed.startsWith("*")) continue;
    
    const words = trimmed.split(/\\s+/);
    if (words.length >= 2 && words.length <= 6) {
      return trimmed.replace(/[.!?:]+$/, "");
    }
  }
  return null;
}

export default function (pi: HookAPI) {
  pi.on("session", async (event, ctx) => {
    if (event.reason === "start" || event.reason === "switch") {
      if (ctx.sessionFile) {
        currentSessionId = path.basename(ctx.sessionFile).replace(".jsonl", "");
        currentCwd = ctx.cwd;
      }
    }
  });

  pi.on("tool_result", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;
    const command = event.input.command as string;
    if (command.includes("git commit") && !event.isError) {
      awaitingTitleResponse = true;
    }
    return undefined;
  });

  pi.on("turn_end", async (event, ctx) => {
    if (!currentSessionId || !currentCwd) return;

    if (awaitingTitleResponse) {
      awaitingTitleResponse = false;
      const sessions = loadSessions(currentCwd);
      const currentTitle = getCurrentTitle(sessions, currentSessionId);

      pi.send(
        `[Session Title] Please provide a 2-4 word title for this session.\\n` +
        `Current title: "${currentTitle}"\\n` +
        `Reply with just the title (2-4 words), or "Title unchanged" to keep it.`
      );
      return;
    }

    const message = event.message;
    if (!message) return;
    const content = message.content;
    if (!Array.isArray(content)) return;

    for (const block of content) {
      if (block.type === "text" && typeof block.text === "string") {
        const title = extractTitle(block.text);
        if (title) {
          updateTitle(currentCwd, currentSessionId, title);
          ctx.ui.notify(`Session titled: ${title}`, "info");
          return;
        }
      }
    }
  });
}
"""
    hook_path.write_text(hook_content)
    click.echo(f"✓ Installed Pi hook: {hook_path}")
    click.echo("")
    click.echo("After git commits, the LLM will be prompted to title the session.")
    click.echo("Titles are saved to .resume-sessions/sessions.json in each repo.")


def install_claude_code_hook():
    """Install Claude Code hook."""
    click.echo("Claude Code hook installation not yet implemented.")
    click.echo("Claude Code uses a different hook system via ~/.claude/settings.json")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
