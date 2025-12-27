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
        sessions = {"test-123": {"titles": ["Test"], "created": "now", "last_updated": "now"}}
        save_sessions(sessions, tmp_repo)
        loaded = load_sessions(tmp_repo)
        assert loaded == sessions

    def test_creates_directory(self, tmp_repo):
        sessions = {"test": {"titles": ["Test"], "created": "now", "last_updated": "now"}}
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


class TestCLI:
    """Tests for CLI commands."""

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
