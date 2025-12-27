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
