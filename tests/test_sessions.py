"""Tests for resume-sessions."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from resume_sessions import (
    cli,
    format_titles,
    get_session,
    load_sessions,
    save_sessions,
    update_session_title,
)


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary repo directory."""
    return tmp_path


class TestFormatTitles:
    """Tests for title formatting."""

    def test_empty_titles(self):
        assert format_titles([]) == "New session"

    def test_single_title(self):
        assert format_titles(["Fix bug"]) == "Fix bug"

    def test_two_titles(self):
        assert format_titles(["Fix bug", "Add tests"]) == "Fix bug · Add tests"

    def test_three_titles(self):
        result = format_titles(["First", "Second", "Third"])
        assert result == "First · Second · Third"

    def test_abbreviates_long_list(self):
        titles = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth"]
        result = format_titles(titles, max_length=40)
        assert "···" in result
        assert "First" in result
        assert "Sixth" in result

    def test_respects_max_length(self):
        titles = ["A very long first title", "Another long title", "Final title"]
        result = format_titles(titles, max_length=50)
        assert len(result) <= 50 or "···" in result


class TestSessionStorage:
    """Tests for session storage."""

    def test_load_empty(self, tmp_repo):
        sessions = load_sessions(tmp_repo)
        assert sessions == {}

    def test_save_and_load(self, tmp_repo):
        sessions = {
            "test-123": {"titles": ["Test"], "created": "now", "last_updated": "now"}
        }
        save_sessions(sessions, tmp_repo)
        loaded = load_sessions(tmp_repo)
        assert loaded == sessions

    def test_creates_directory(self, tmp_repo):
        sessions = {
            "test": {"titles": ["Test"], "created": "now", "last_updated": "now"}
        }
        save_sessions(sessions, tmp_repo)
        assert (tmp_repo / ".resume-sessions" / "sessions.json").exists()


class TestGetSession:
    """Tests for get_session."""

    def test_creates_new_session(self, tmp_repo):
        session = get_session("new-session", tmp_repo)
        assert session["titles"] == ["New session"]
        assert "created" in session
        assert "last_updated" in session

    def test_returns_existing_session(self, tmp_repo):
        # Create a session first
        update_session_title("existing", "Custom Title", tmp_repo)

        # Get it again
        session = get_session("existing", tmp_repo)
        assert "Custom Title" in session["titles"]


class TestUpdateSessionTitle:
    """Tests for update_session_title."""

    def test_creates_session_if_not_exists(self, tmp_repo):
        session = update_session_title("new", "First Title", tmp_repo)
        assert "New session" in session["titles"]
        assert "First Title" in session["titles"]

    def test_appends_different_title(self, tmp_repo):
        update_session_title("test", "First", tmp_repo)
        session = update_session_title("test", "Second", tmp_repo)
        assert session["titles"] == ["New session", "First", "Second"]

    def test_does_not_append_same_title(self, tmp_repo):
        update_session_title("test", "Same", tmp_repo)
        session = update_session_title("test", "Same", tmp_repo)
        # Should have: New session, Same (not duplicated)
        assert session["titles"].count("Same") == 1


class TestFindPiSessions:
    """Tests for Pi session discovery."""

    def test_finds_sessions_in_project_dir(self, tmp_path):
        """Find sessions stored in project subdirectories."""
        from resume_sessions import find_pi_sessions

        # Create mock Pi sessions directory structure
        sessions_dir = tmp_path / "sessions"
        project_dir = sessions_dir / "--Users-test-myproject--"
        project_dir.mkdir(parents=True)

        # Create some session files
        (project_dir / "2025-01-01T00-00-00_abc123.jsonl").write_text("{}")
        (project_dir / "2025-01-02T00-00-00_def456.jsonl").write_text("{}")

        sessions = find_pi_sessions(sessions_dir)
        assert len(sessions) == 2

    def test_returns_session_info(self, tmp_path):
        """Session info includes path, id, project, and timestamp."""
        from resume_sessions import find_pi_sessions

        sessions_dir = tmp_path / "sessions"
        project_dir = sessions_dir / "--Users-test-myproject--"
        project_dir.mkdir(parents=True)
        (project_dir / "2025-01-15T10-30-00_abc123.jsonl").write_text("{}")

        sessions = find_pi_sessions(sessions_dir)
        assert len(sessions) == 1
        s = sessions[0]
        assert s["id"] == "2025-01-15T10-30-00_abc123"
        assert s["project"] == "--Users-test-myproject--"
        assert "path" in s


class TestResumeDisplay:
    """Tests for resume display with titles."""

    def test_formats_session_with_title(self, tmp_path):
        """Format a session that has a title."""
        from resume_sessions import format_resume_line

        session_info = {
            "id": "2025-01-15T10-30-00_abc123",
            "project": "--Users-test-myproject--",
            "path": tmp_path / "session.jsonl",
        }
        titles = ["Initial setup", "Add feature X"]

        line = format_resume_line(session_info, titles)
        assert "2025-01-15" in line
        assert "myproject" in line
        assert "Add feature X" in line

    def test_formats_session_without_title(self, tmp_path):
        """Format a session with no title data."""
        from resume_sessions import format_resume_line

        session_info = {
            "id": "2025-01-15T10-30-00_abc123",
            "project": "--Users-test-myproject--",
            "path": tmp_path / "session.jsonl",
        }

        line = format_resume_line(session_info, None)
        assert "2025-01-15" in line
        assert "myproject" in line
        assert "(no title)" in line or "New session" in line


class TestRelativeTime:
    """Tests for relative time formatting."""

    def test_just_now(self):
        from datetime import datetime, timezone
        from resume_sessions import format_relative_time

        now = datetime.now(timezone.utc)
        assert format_relative_time(now) == "just now"

    def test_minutes_ago(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        assert format_relative_time(past) == "5 minutes ago"

    def test_one_minute_ago(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert format_relative_time(past) == "1 minute ago"

    def test_hours_ago(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(hours=3)
        assert format_relative_time(past) == "3 hours ago"

    def test_one_hour_ago(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        assert format_relative_time(past) == "1 hour ago"

    def test_days_ago(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(days=2)
        assert format_relative_time(past) == "2 days ago"

    def test_one_day_ago(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(days=1)
        assert format_relative_time(past) == "1 day ago"

    def test_weeks_ago(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(days=14)
        assert format_relative_time(past) == "2 weeks ago"

    def test_older_shows_date(self):
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_relative_time

        past = datetime.now(timezone.utc) - timedelta(days=60)
        result = format_relative_time(past)
        # Should show actual date for older than ~4 weeks
        assert "ago" not in result or "weeks" in result


class TestSessionParsing:
    """Tests for parsing Pi session files."""

    def test_parse_first_message(self, tmp_path):
        """Extract first user message from session file."""
        from resume_sessions import parse_session_file

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type":"session","data":{}}\n'
            '{"type":"message","message":{"role":"user","content":[{"type":"text","text":"Fix the bug in auth.py"}]}}\n'
            '{"type":"message","message":{"role":"assistant","content":[{"type":"text","text":"I will fix it."}]}}\n'
        )

        info = parse_session_file(session_file)
        assert info["first_message"] == "Fix the bug in auth.py"
        assert info["message_count"] >= 2

    def test_parse_empty_session(self, tmp_path):
        """Handle empty or malformed session files."""
        from resume_sessions import parse_session_file

        session_file = tmp_path / "session.jsonl"
        session_file.write_text("")

        info = parse_session_file(session_file)
        assert info["first_message"] == ""
        assert info["message_count"] == 0

    def test_parse_counts_messages(self, tmp_path):
        """Count total messages in session."""
        from resume_sessions import parse_session_file

        session_file = tmp_path / "session.jsonl"
        lines = [
            '{"type":"message","message":{"role":"user","content":[{"type":"text","text":"Hello"}]}}',
            '{"type":"message","message":{"role":"assistant","content":[{"type":"text","text":"Hi"}]}}',
            '{"type":"message","message":{"role":"user","content":[{"type":"text","text":"Bye"}]}}',
        ]
        session_file.write_text("\n".join(lines))

        info = parse_session_file(session_file)
        assert info["message_count"] == 3


class TestEnhancedResumeDisplay:
    """Tests for enhanced resume display format."""

    def test_format_includes_relative_time(self, tmp_path):
        """Display uses relative time instead of ISO date."""
        from datetime import datetime, timezone, timedelta
        from resume_sessions import format_resume_line_enhanced

        session_info = {
            "id": "2025-01-15T10-30-00_abc123",
            "project": "--Users-test-myproject--",
            "path": tmp_path / "session.jsonl",
            "modified": datetime.now(timezone.utc) - timedelta(hours=2),
            "first_message": "Fix the authentication bug",
            "message_count": 15,
        }
        titles = ["Fix auth bug"]

        line = format_resume_line_enhanced(session_info, titles)
        assert "2 hours ago" in line
        assert "15 messages" in line

    def test_format_truncates_long_message(self, tmp_path):
        """First message is truncated if too long."""
        from datetime import datetime, timezone
        from resume_sessions import format_resume_line_enhanced

        long_message = "This is a very long first message that should be truncated because it exceeds the maximum display width for the terminal"
        session_info = {
            "id": "2025-01-15T10-30-00_abc123",
            "project": "--Users-test-myproject--",
            "path": tmp_path / "session.jsonl",
            "modified": datetime.now(timezone.utc),
            "first_message": long_message,
            "message_count": 5,
        }
        titles = ["Some task"]

        line = format_resume_line_enhanced(session_info, titles)
        assert "..." in line
        assert len(line.split("\n")[0]) <= 100  # Reasonable line length


class TestCLI:
    """Tests for CLI commands."""

    def test_resume_command_no_sessions(self, tmp_path, monkeypatch):
        """Test resume command with no sessions."""
        from resume_sessions import cli
        import resume_sessions

        # Mock the sessions dir to an empty temp dir
        monkeypatch.setattr(
            resume_sessions, "get_pi_sessions_dir", lambda: tmp_path / "sessions"
        )
        (tmp_path / "sessions").mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["resume"])
        assert result.exit_code == 0
        assert "No Pi sessions found" in result.output

    def test_resume_command_with_sessions(self, tmp_path, monkeypatch):
        """Test resume command displays sessions."""
        from resume_sessions import cli
        import resume_sessions

        # Create mock Pi sessions directory
        sessions_dir = tmp_path / "sessions"
        project_dir = sessions_dir / "--mock-project--"
        project_dir.mkdir(parents=True)
        # Create a session with actual content
        session_content = (
            '{"type":"message","message":{"role":"user","content":[{"type":"text","text":"Hello world"}]}}\n'
            '{"type":"message","message":{"role":"assistant","content":[{"type":"text","text":"Hi!"}]}}\n'
        )
        (project_dir / "2025-01-15T10-30-00_abc123.jsonl").write_text(session_content)

        # Mock the sessions dir
        monkeypatch.setattr(
            resume_sessions, "get_pi_sessions_dir", lambda: sessions_dir
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["resume"])
        assert result.exit_code == 0
        # Enhanced format shows project path and messages
        assert "project" in result.output
        assert "messages" in result.output
        assert "Hello world" in result.output

    def test_title_command(self, tmp_repo, monkeypatch):
        monkeypatch.chdir(tmp_repo)
        runner = CliRunner()
        result = runner.invoke(cli, ["title", "test-session", "My Title"])
        assert result.exit_code == 0
        assert "My Title" in result.output

    def test_show_command(self, tmp_repo, monkeypatch):
        monkeypatch.chdir(tmp_repo)
        runner = CliRunner()

        # Create a session first
        runner.invoke(cli, ["title", "test-session", "Test Title"])

        # Show it
        result = runner.invoke(cli, ["show", "test-session"])
        assert result.exit_code == 0
        assert "Test Title" in result.output

    def test_list_command_empty(self, tmp_repo, monkeypatch):
        monkeypatch.chdir(tmp_repo)
        runner = CliRunner()
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "No sessions found" in result.output

    def test_list_command_with_sessions(self, tmp_repo, monkeypatch):
        monkeypatch.chdir(tmp_repo)
        runner = CliRunner()

        # Create sessions
        runner.invoke(cli, ["title", "session-1", "First Session"])
        runner.invoke(cli, ["title", "session-2", "Second Session"])

        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "session-1" in result.output
        assert "session-2" in result.output
