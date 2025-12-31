"""LLM-generated session titles for AI coding agents."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.text import Text


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

    Shows (per spec):
      Line 1: Title (bold) - OR first message if no title
      Line 2: First message (dimmed) - only if title was shown on line 1
      Line 3: time · messages · project

    Args:
        session_info: dict with id, project, path, modified, first_message, message_count
        titles: list of titles or None if no title data

    Returns:
        Multi-line formatted string
    """
    # Format first message (truncated)
    first_msg = session_info.get("first_message", "")
    first_msg = " ".join(first_msg.split())  # Normalize whitespace
    max_msg_len = 70
    if len(first_msg) > max_msg_len:
        first_msg = first_msg[: max_msg_len - 3] + "..."

    # Format relative time
    modified = session_info.get("modified")
    if isinstance(modified, datetime):
        time_str = format_relative_time(modified)
    else:
        time_str = "unknown"

    # Format message count
    count = session_info.get("message_count", 0)
    count_str = f"{count} message{'s' if count != 1 else ''}"

    # Format project path
    project_path = project_name_to_path(session_info.get("project", ""))
    if len(project_path) > 25:
        project_path = "..." + project_path[-22:]

    # Build output
    lines = []

    if titles:
        # Has title: show title on line 1, first message on line 2
        title_str = format_titles(titles, max_length=70)
        lines.append(click.style(title_str, bold=True))
        if first_msg:
            lines.append(click.style(f"  {first_msg}", dim=True))
    else:
        # No title: show first message on line 1 (as fallback)
        if first_msg:
            lines.append(click.style(first_msg, bold=True))
        else:
            lines.append(click.style("(empty session)", bold=True))

    # Final line: metadata
    meta = f"  {time_str} · {count_str} · {project_path}"
    lines.append(click.style(meta, dim=True))

    return "\n".join(lines)


def fuzzy_filter_sessions(sessions: list[dict], query: str) -> list[dict]:
    """Filter sessions by fuzzy search query.

    Searches in:
      - project name/path
      - first message
      - titles (if available in session_info)

    Args:
        sessions: List of session info dicts
        query: Search query string

    Returns:
        Filtered list of sessions matching the query
    """
    if not query:
        return sessions

    query_lower = query.lower()
    results = []

    for session in sessions:
        # Search in project name
        project = session.get("project", "")
        project_path = project_name_to_path(project)

        # Search in first message
        first_msg = session.get("first_message", "")

        # Search in titles if present
        titles = session.get("titles", [])
        titles_text = " ".join(titles) if titles else ""

        # Combine searchable text
        searchable = f"{project} {project_path} {first_msg} {titles_text}".lower()

        if query_lower in searchable:
            results.append(session)

    return results


def build_session_choices(
    sessions: list[dict], titles_map: dict[str, list[str]]
) -> list[dict]:
    """Build choices for interactive session selector.

    Args:
        sessions: List of session info dicts
        titles_map: Map of session_id -> list of titles

    Returns:
        List of choice dicts with all info needed for display
    """
    choices = []

    for session in sessions:
        session_id = session["id"]
        titles = titles_map.get(session_id, [])
        project_path = project_name_to_path(session.get("project", ""))

        # Get first message (truncated)
        first_msg = session.get("first_message", "")
        first_msg = " ".join(first_msg.split())  # Normalize whitespace

        # Get relative time
        modified = session.get("modified")
        if isinstance(modified, datetime):
            time_str = format_relative_time(modified)
        else:
            time_str = ""

        # Get message count
        count = session.get("message_count", 0)

        # Format title if available
        title_str = ""
        if titles:
            title_str = format_titles(titles, max_length=50)

        # Build searchable text for filtering
        searchable = f"{project_path} {first_msg} {title_str}".lower()

        choices.append(
            {
                "session_id": session_id,
                "first_message": first_msg,
                "title": title_str,
                "project": project_path,
                "time": time_str,
                "message_count": count,
                "searchable": searchable,
            }
        )

    return choices


def run_interactive_selector(
    sessions: list[dict], titles_map: dict[str, list[str]]
) -> Optional[str]:
    """Run interactive session selector using rich.

    Display format (2 lines per session, like Pi/Claude Code):
      › First message truncated to fit terminal width...
        3 hours ago · 26 messages · ~/project · [Title if available]

    Args:
        sessions: List of session info dicts
        titles_map: Map of session_id -> list of titles

    Returns:
        Selected session_id or None if cancelled
    """
    import shutil
    import sys
    import termios
    import tty

    console = Console()
    choices = build_session_choices(sessions, titles_map)

    if not choices:
        console.print("[yellow]No sessions available[/yellow]")
        return None

    selected_idx = 0
    scroll_offset = 0
    search_query = ""
    search_mode = False
    max_visible = 8

    # Get terminal width
    term_width = shutil.get_terminal_size().columns

    def get_filtered_choices():
        if not search_query:
            return choices
        query_lower = search_query.lower()
        return [c for c in choices if query_lower in c["searchable"]]

    def adjust_scroll():
        """Adjust scroll_offset to keep selected_idx visible."""
        nonlocal scroll_offset
        if selected_idx < scroll_offset:
            scroll_offset = selected_idx
        elif selected_idx >= scroll_offset + max_visible:
            scroll_offset = selected_idx - max_visible + 1

    def render_session(choice, is_selected, width):
        """Render a single session (2-3 lines per spec).

        With title:    Title (bold)
                       First message (dim)
                       time · messages · project

        Without title: First message (bold)
                       time · messages · project
        """
        lines = []
        cursor = "› " if is_selected else "  "
        max_text_len = width - 4  # Account for cursor and padding

        has_title = bool(choice["title"])
        first_msg = choice["first_message"] or "(empty session)"
        if len(first_msg) > max_text_len:
            first_msg = first_msg[: max_text_len - 3] + "..."

        if has_title:
            # Line 1: Title
            title = choice["title"]
            if len(title) > max_text_len:
                title = title[: max_text_len - 3] + "..."
            if is_selected:
                lines.append(f"[bold cyan]{cursor}{title}[/bold cyan]")
            else:
                lines.append(f"{cursor}{title}")

            # Line 2: First message (dimmed)
            if choice["first_message"]:
                lines.append(f"[dim]    {first_msg}[/dim]")
        else:
            # No title: Line 1 is first message
            if is_selected:
                lines.append(f"[bold cyan]{cursor}{first_msg}[/bold cyan]")
            else:
                lines.append(f"{cursor}{first_msg}")

        # Final line: Metadata
        meta_parts = []
        if choice["time"]:
            meta_parts.append(choice["time"])
        meta_parts.append(f"{choice['message_count']} messages")
        meta_parts.append(choice["project"])

        meta_line = "    " + " · ".join(meta_parts)
        if len(meta_line) > width:
            meta_line = meta_line[: width - 3] + "..."

        lines.append(f"[dim]{meta_line}[/dim]")

        return lines

    def render():
        nonlocal scroll_offset
        console.clear()
        console.print(
            "[bold]Resume Session[/bold]  ↑↓ navigate · Enter select · / search · q quit\n"
        )

        filtered = get_filtered_choices()

        # Show search prompt
        if search_mode or search_query:
            console.print(f"[cyan]Search: {search_query}_[/cyan]\n")

        if not filtered:
            console.print("[dim]No matching sessions[/dim]")
            return filtered

        # Ensure scroll_offset is valid for filtered results
        if scroll_offset > len(filtered) - max_visible:
            scroll_offset = max(0, len(filtered) - max_visible)

        # Show sessions from scroll_offset
        visible_end = min(scroll_offset + max_visible, len(filtered))
        for i in range(scroll_offset, visible_end):
            choice = filtered[i]
            lines = render_session(choice, i == selected_idx, term_width)
            for line in lines:
                console.print(line)
            if i < visible_end - 1:
                console.print()  # Blank line between sessions

        # Show scroll indicator
        if len(filtered) > max_visible:
            showing = f"{scroll_offset + 1}-{visible_end} of {len(filtered)}"
            console.print(f"\n[dim]{showing}[/dim]")

        return filtered

    def getch():
        """Read a single character from stdin."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            # Handle escape sequences (arrow keys)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    return f"\x1b[{ch3}"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    try:
        while True:
            adjust_scroll()
            filtered = render()

            ch = getch()

            if ch == "q" or ch == "\x03":  # q or Ctrl+C
                console.clear()
                return None
            elif ch == "\x1b[A":  # Up arrow
                selected_idx = max(0, selected_idx - 1)
            elif ch == "\x1b[B":  # Down arrow
                selected_idx = (
                    min(len(filtered) - 1, selected_idx + 1) if filtered else 0
                )
            elif ch == "\r" or ch == "\n":  # Enter
                if search_mode:
                    search_mode = False  # Exit search mode on Enter
                elif filtered and 0 <= selected_idx < len(filtered):
                    console.clear()
                    return filtered[selected_idx]["session_id"]
            elif ch == "/":  # Start search
                search_mode = True
                search_query = ""
                selected_idx = 0
                scroll_offset = 0
            elif ch == "\x7f":  # Backspace
                if search_query:
                    search_query = search_query[:-1]
                    selected_idx = 0
                    scroll_offset = 0
            elif ch == "\x1b":  # Escape - clear search
                search_mode = False
                search_query = ""
                selected_idx = 0
                scroll_offset = 0
            elif search_mode and ch.isprintable():
                search_query += ch
                selected_idx = 0
                scroll_offset = 0

    except KeyboardInterrupt:
        console.clear()
        return None


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
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Interactive mode with search and selection",
)
@click.option(
    "--run", is_flag=True, help="Run pi --resume with selected session (implies -i)"
)
def resume(
    limit: int, project: Optional[str], simple: bool, interactive: bool, run: bool
):
    """Show recent Pi sessions with their titles.

    Discovers sessions from ~/.pi/agent/sessions/ and matches them
    with titles from each project's .resume-sessions/sessions.json

    Examples:

        resume-sessions resume              # Show last 10 sessions

        resume-sessions resume -n 5         # Show last 5 sessions

        resume-sessions resume -p dashboard # Filter by project name

        resume-sessions resume -i           # Interactive mode

        resume-sessions resume --run        # Select and resume a session
    """
    # --run implies interactive
    if run:
        interactive = True

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

    # Limit results (for non-interactive mode)
    if not interactive:
        sessions = sessions[:limit]

    if not sessions:
        click.echo("No matching sessions found.")
        return

    # Enrich sessions with parsed data
    for session_info in sessions:
        parsed = parse_session_file(session_info["path"])
        session_info.update(parsed)

    # Build titles map
    titles_map = {}
    for session_info in sessions:
        project_path = project_name_to_path(session_info["project"])
        titles = load_titles_for_session(session_info["id"], project_path)
        if titles:
            titles_map[session_info["id"]] = titles

    if interactive:
        selected_id = run_interactive_selector(sessions, titles_map)
        if selected_id:
            if run:
                # Find the session to get project path for cd
                selected_session = next(
                    (s for s in sessions if s["id"] == selected_id), None
                )
                if selected_session:
                    project_path = project_name_to_path(selected_session["project"])
                    click.echo(f"Resuming session in {project_path}...")
                    # Run pi --resume with the session ID
                    subprocess.run(["pi", "--resume", selected_id])
            else:
                # Just print the session ID for use with pi --resume
                click.echo(f"\nSelected: {selected_id}")
                click.echo(f"\nTo resume: pi --resume {selected_id}")
    else:
        for i, session_info in enumerate(sessions):
            titles = titles_map.get(session_info["id"])

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

    # Hook content: extracts commit message and uses first line as title
    hook_content = """/**
 * Pi agent hook for resume-sessions.
 * After a successful git commit, extracts the commit message and uses it as the session title.
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

function updateTitle(cwd: string, sessionId: string, newTitle: string): void {
  const sessions = loadSessions(cwd);
  const now = new Date().toISOString();
  
  if (!sessions[sessionId]) {
    sessions[sessionId] = {
      titles: [],
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

function extractCommitMessage(command: string): string | null {
  // Match -m "message" or -m 'message'
  const match = command.match(/-m\\s+["']([^"']+)["']/);
  if (!match) return null;
  
  // Take only the first line (before any newline)
  const fullMessage = match[1];
  const firstLine = fullMessage.split('\\n')[0].trim();
  return firstLine || null;
}

function extractCwd(command: string, defaultCwd: string): string {
  const cdMatch = command.match(/cd\\s+([^\\s&;]+)/);
  if (cdMatch) {
    let targetDir = cdMatch[1];
    if (targetDir.startsWith("~")) {
      targetDir = targetDir.replace("~", process.env.HOME || "");
    }
    return path.resolve(defaultCwd, targetDir);
  }
  return defaultCwd;
}

export default function (pi: HookAPI) {
  // Track session ID and cwd
  pi.on("session", async (event, ctx) => {
    if (event.reason === "start" || event.reason === "switch") {
      if (ctx.sessionFile) {
        currentSessionId = path.basename(ctx.sessionFile).replace(".jsonl", "");
        currentCwd = ctx.cwd;
      }
    }
  });

  // Detect successful git commit and extract commit message as title
  pi.on("tool_result", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;

    const command = event.input.command as string;
    
    if (command.includes("git commit") && !event.isError) {
      const commitMessage = extractCommitMessage(command);
      if (!commitMessage) {
        return undefined;
      }
      
      const cwd = extractCwd(command, ctx.cwd);
      
      if (currentSessionId) {
        updateTitle(cwd, currentSessionId, commitMessage);
      }
    }
    return undefined;
  });
}
"""
    hook_path.write_text(hook_content)
    click.echo(f"✓ Installed Pi hook: {hook_path}")
    click.echo("")
    click.echo(
        "After git commits, the commit message (first line) becomes the session title."
    )
    click.echo("Titles are saved to .resume-sessions/sessions.json in each repo.")


def install_claude_code_hook():
    """Install Claude Code hook."""
    hooks_dir = Path.home() / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Write the hook script
    hook_script = hooks_dir / "resume-sessions-hook.py"
    hook_content = '''#!/usr/bin/env python3
"""
Claude Code hook for resume-sessions.
After a successful git commit, extracts the commit message and saves it as the session title.

Input: JSON via stdin with PostToolUse data
Output: None (just logs to sessions.json)
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def extract_commit_message(command: str) -> str | None:
    """Extract commit message from git commit command."""
    # Match -m "message" or -m 'message'
    match = re.search(r'-m\\s+["\\'](.*?)["\\']', command, re.DOTALL)
    if not match:
        return None
    
    # Take only the first line
    full_message = match.group(1)
    first_line = full_message.split('\\n')[0].strip()
    return first_line if first_line else None


def load_sessions(cwd: str) -> dict:
    """Load sessions from the project's sessions.json."""
    sessions_file = Path(cwd) / ".resume-sessions" / "sessions.json"
    try:
        if sessions_file.exists():
            return json.loads(sessions_file.read_text())
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def save_sessions(cwd: str, sessions: dict) -> None:
    """Save sessions to the project's sessions.json."""
    sessions_dir = Path(cwd) / ".resume-sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    sessions_file = sessions_dir / "sessions.json"
    sessions_file.write_text(json.dumps(sessions, indent=2))


def update_title(cwd: str, session_id: str, new_title: str) -> None:
    """Update the session title."""
    sessions = load_sessions(cwd)
    now = datetime.utcnow().isoformat() + "Z"
    
    if session_id not in sessions:
        sessions[session_id] = {
            "titles": [],
            "created": now,
            "last_updated": now,
        }
    
    session = sessions[session_id]
    current_title = session["titles"][-1] if session["titles"] else None
    
    # Only append if different
    if new_title != current_title:
        session["titles"].append(new_title)
    
    session["last_updated"] = now
    save_sessions(cwd, sessions)
    
    # Update terminal tab title
    sys.stdout.write(f"\\033]0;{new_title}\\007")
    sys.stdout.flush()


def main():
    # Read hook input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    
    # Only handle PostToolUse for Bash
    if input_data.get("hook_event_name") != "PostToolUse":
        return
    if input_data.get("tool_name") != "Bash":
        return
    
    # Get the command from tool_input
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")
    
    # Check if it's a git commit
    if "git commit" not in command:
        return
    
    # Check if the tool succeeded (no error in stderr)
    tool_response = input_data.get("tool_response", {})
    if tool_response.get("stderr") and "error" in tool_response.get("stderr", "").lower():
        return
    
    # Extract commit message
    commit_message = extract_commit_message(command)
    if not commit_message:
        return
    
    # Get session ID and cwd
    session_id = input_data.get("session_id", "")
    cwd = input_data.get("cwd", os.getcwd())
    
    if session_id:
        update_title(cwd, session_id, commit_message)


if __name__ == "__main__":
    main()
'''
    hook_script.write_text(hook_content)
    hook_script.chmod(0o755)
    click.echo(f"✓ Created hook script: {hook_script}")

    # Update settings.json
    settings_file = Path.home() / ".claude" / "settings.json"
    try:
        if settings_file.exists():
            settings = json.loads(settings_file.read_text())
        else:
            settings = {}
    except json.JSONDecodeError:
        settings = {}

    # Ensure hooks structure exists
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PostToolUse" not in settings["hooks"]:
        settings["hooks"]["PostToolUse"] = []

    # Check if hook already exists
    post_hooks = settings["hooks"]["PostToolUse"]
    hook_exists = any(
        "resume-sessions-hook.py" in h.get("hooks", [{}])[0].get("command", "")
        for h in post_hooks
        if h.get("hooks")
    )

    if not hook_exists:
        new_hook = {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": str(hook_script)}],
        }
        post_hooks.append(new_hook)
        settings_file.write_text(json.dumps(settings, indent=2))
        click.echo(f"✓ Added hook to: {settings_file}")
    else:
        click.echo(f"✓ Hook already configured in: {settings_file}")

    click.echo("")
    click.echo(
        "After git commits, the commit message (first line) becomes the session title."
    )
    click.echo("Titles are saved to .resume-sessions/sessions.json in each repo.")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
